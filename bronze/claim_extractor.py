import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


PERIOD_TERMS = [
    "夏代晚期", "夏代早期", "夏代", "商代早期", "商代中期", "商代晚期", "商代",
    "西周早期", "西周中期", "西周晚期", "西周", "春秋早期", "春秋中期", "春秋晚期",
    "春秋时期", "春秋", "战国早期", "战国中期", "战国晚期", "战国时期", "战国",
    "秦代", "西汉", "东汉", "汉代", "唐代", "宋代", "元代", "明代", "清代",
]

FIELD_PATTERNS = {
    "period": PERIOD_TERMS,
    "collection": ["现藏", "收藏", "藏于", "馆藏"],
    "excavation": ["出土", "传出土"],
    "inscription": ["铭文", "铸铭", "刻铭"],
    "decoration": ["纹", "纹饰", "饰"],
    "function": ["器", "用途", "盛", "饮酒", "肉食", "饭食", "盛水", "照容", "兵器"],
    "dimension": ["高", "长", "宽", "口径", "底径", "通高", "直径", "厘米", "cm"],
    "weight": ["重", "千克", "克", "公斤", "kg"],
}

MISSING_MARKERS = ["未记载", "没有记载", "资料不足", "无相关记录", "无法确认", "不能确定", "未提供"]
CORRECTION_MARKERS = ["并非", "不是", "不符", "错误", "纠正", "修正", "应为", "而不是", "矛盾", "冲突"]


@dataclass
class ExtractedClaim:
    claim_id: str
    claim_text: str
    subject: str = ""
    subject_id: str = ""
    field: str = "general"
    value: str = ""
    claim_type: str = "artifact_fact"
    confidence: float = 0.6
    extraction_method: str = "rules"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "subject": self.subject,
            "subject_id": self.subject_id,
            "field": self.field,
            "value": self.value,
            "claim_type": self.claim_type,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
        }


class HybridClaimExtractor:
    """Rule-first claim extractor. LLM fallback can be added later."""

    version = "hybrid_rules_v1"

    def extract(
        self,
        *,
        answer_id: str,
        answer_text: str,
        question: str = "",
        target_item_ids: Optional[List[Any]] = None,
        max_claims: int = 24,
    ) -> List[Dict[str, Any]]:
        subject = first_artifact_name(answer_text) or first_artifact_name(question)
        subject_ids = extract_item_ids(answer_text) or extract_item_ids(question)
        if target_item_ids:
            for item_id in target_item_ids:
                if str(item_id) not in subject_ids:
                    subject_ids.append(str(item_id))

        claims: List[ExtractedClaim] = []
        for index, sentence in enumerate(split_claim_sentences(strip_json_block(answer_text)), start=1):
            field = infer_field(sentence)
            claim_type = infer_claim_type(sentence)
            values = extract_values(sentence, field)
            if not values:
                values = [""]
            for value in values:
                claim = ExtractedClaim(
                    claim_id=stable_id("claim", answer_id, index, sentence, value),
                    claim_text=sentence,
                    subject=subject,
                    subject_id=subject_ids[0] if subject_ids else "",
                    field=field,
                    value=value,
                    claim_type=claim_type,
                    confidence=confidence_for(field, claim_type, value),
                )
                claims.append(claim)
                if len(claims) >= max_claims:
                    return dedupe_claims(claims)
        return dedupe_claims(claims)


def split_claim_sentences(text: str) -> List[str]:
    parts = []
    for raw in re.split(r"[。；;\n]+", text):
        part = raw.strip(" 　-*#：:")
        if len(part) < 8:
            continue
        if is_process_text(part):
            continue
        parts.append(part)
    return parts


def is_process_text(text: str) -> bool:
    process_markers = [
        "请其他成员", "小组成员", "最终协同回答", "我建议我们", "协作", "下面给出",
        "JSON", "used_memory_ids", "derived_from",
    ]
    return any(marker in text for marker in process_markers)


def infer_claim_type(text: str) -> str:
    if any(marker in text for marker in MISSING_MARKERS):
        return "missing_info_statement"
    if any(marker in text for marker in CORRECTION_MARKERS):
        return "correction_statement"
    if "可能" in text or "推测" in text:
        return "inference"
    return "artifact_fact"


def infer_field(text: str) -> str:
    for period in PERIOD_TERMS:
        if period in text:
            return "period"
    for field, markers in FIELD_PATTERNS.items():
        if field == "period":
            continue
        if any(marker in text for marker in markers):
            return field
    if re.search(r"\d+(?:\.\d+)?\s*(?:厘米|cm|CM)", text):
        return "dimension"
    return "general"


def extract_values(text: str, field: str) -> List[str]:
    if field == "period":
        return [term for term in PERIOD_TERMS if term in text]
    if field == "dimension":
        return re.findall(r"(?:高|长|宽|口径|底径|通高|直径)?\s*\d+(?:\.\d+)?\s*(?:厘米|cm|CM)", text)
    if field == "weight":
        return re.findall(r"(?:重)?\s*\d+(?:\.\d+)?\s*(?:千克|公斤|克|kg|KG)", text)
    if field in {"collection", "excavation"}:
        return [text]
    quoted = re.findall(r"“([^”]+)”", text)
    if quoted:
        return quoted
    return []


def confidence_for(field: str, claim_type: str, value: str) -> float:
    if claim_type in {"missing_info_statement", "correction_statement"}:
        return 0.8
    if field in {"period", "dimension", "weight"} and value:
        return 0.85
    if field != "general":
        return 0.7
    return 0.55


def first_artifact_name(text: str) -> str:
    match = re.search(r"《([^》]+)》", text)
    return match.group(1).strip() if match else ""


def extract_item_ids(text: str) -> List[str]:
    ids = []
    for match in re.finditer(r"(?:ID|KB_)\s*[:：]?\s*(\d{5,})", text):
        if match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def strip_json_block(text: str) -> str:
    return re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL).strip()


def dedupe_claims(claims: List[ExtractedClaim]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for claim in claims:
        key = (claim.claim_text, claim.field, claim.value)
        if key in seen:
            continue
        seen.add(key)
        result.append(claim.to_dict())
    return result


def stable_id(prefix: str, *parts: Any) -> str:
    text = "\u241f".join(str(part) for part in parts)
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"
