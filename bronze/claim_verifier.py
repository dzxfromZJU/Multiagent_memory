import re
from dataclasses import dataclass
from typing import Any, Dict, List

from bronze.claim_extractor import PERIOD_TERMS


VERDICT_SUPPORTS = "supports"
VERDICT_CONTRADICTS = "contradicts"
VERDICT_PARTIAL = "partially_supports"
VERDICT_INSUFFICIENT = "insufficient_evidence"
VERDICT_NOT_APPLICABLE = "not_applicable"


@dataclass
class EvidenceSource:
    source_id: str
    source_type: str
    text: str


@dataclass
class VerificationResult:
    claim_id: str
    source_id: str
    source_type: str
    verdict: str
    confidence: float
    evidence_quote: str = ""
    reason: str = ""
    method: str = "rules"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "evidence_quote": self.evidence_quote,
            "reason": self.reason,
            "method": self.method,
        }


class HybridClaimVerifier:
    """Rule-first claim verifier. LLM fallback can be added later."""

    version = "hybrid_rules_v1"

    def verify(self, claim: Dict[str, Any], evidence_sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for source in evidence_sources:
            evidence = EvidenceSource(
                source_id=str(source.get("source_id", "")),
                source_type=str(source.get("source_type", "")),
                text=str(source.get("text", "")),
            )
            if not evidence.source_id or not evidence.text:
                continue
            results.append(self.verify_one(claim, evidence).to_dict())
        if not results:
            results.append(
                VerificationResult(
                    claim_id=str(claim.get("claim_id", "")),
                    source_id="",
                    source_type="",
                    verdict=VERDICT_INSUFFICIENT,
                    confidence=0.2,
                    reason="no evidence source was provided",
                ).to_dict()
            )
        return results

    def verify_one(self, claim: Dict[str, Any], evidence: EvidenceSource) -> VerificationResult:
        claim_id = str(claim.get("claim_id", ""))
        claim_text = str(claim.get("claim_text", ""))
        claim_type = str(claim.get("claim_type", ""))
        field = str(claim.get("field", "general"))
        value = str(claim.get("value", "")).strip()

        if claim_type == "missing_info_statement":
            return verify_missing_info(claim_id, field, claim_text, evidence)
        if value and value in evidence.text:
            return VerificationResult(
                claim_id,
                evidence.source_id,
                evidence.source_type,
                VERDICT_SUPPORTS,
                0.95,
                evidence_quote=quote_around(evidence.text, value),
                reason="claim value appears exactly in evidence",
            )
        if field == "period":
            return verify_period(claim_id, claim_text, value, evidence)
        if field in {"dimension", "weight"}:
            return verify_numeric_field(claim_id, field, claim_text, value, evidence)
        if field in {"collection", "excavation", "inscription", "decoration", "function"}:
            return verify_text_field(claim_id, field, claim_text, value, evidence)
        return verify_general(claim_id, claim_text, evidence)


def verify_period(claim_id: str, claim_text: str, value: str, evidence: EvidenceSource) -> VerificationResult:
    claim_periods = set([value] if value else extract_periods(claim_text))
    evidence_periods = set(extract_periods(evidence.text))
    if claim_periods and evidence_periods:
        if claim_periods & evidence_periods:
            period = next(iter(claim_periods & evidence_periods))
            return VerificationResult(
                claim_id, evidence.source_id, evidence.source_type,
                VERDICT_SUPPORTS, 0.92, quote_around(evidence.text, period),
                "period matches evidence",
            )
        return VerificationResult(
            claim_id, evidence.source_id, evidence.source_type,
            VERDICT_CONTRADICTS, 0.88, ";".join(sorted(evidence_periods)),
            "claim period conflicts with evidence period",
        )
    return insufficient(claim_id, evidence, "no explicit period evidence found")


def verify_numeric_field(
    claim_id: str,
    field: str,
    claim_text: str,
    value: str,
    evidence: EvidenceSource,
) -> VerificationResult:
    claim_numbers = set(extract_numbers(value or claim_text))
    evidence_numbers = set(extract_numbers(evidence.text))
    if claim_numbers and evidence_numbers:
        if claim_numbers & evidence_numbers:
            number = next(iter(claim_numbers & evidence_numbers))
            return VerificationResult(
                claim_id, evidence.source_id, evidence.source_type,
                VERDICT_SUPPORTS, 0.9, quote_around(evidence.text, number),
                f"{field} numeric value matches evidence",
            )
        if field in evidence.text or any(marker in evidence.text for marker in ("高", "重", "口径", "厘米", "千克")):
            return VerificationResult(
                claim_id, evidence.source_id, evidence.source_type,
                VERDICT_CONTRADICTS, 0.75, ",".join(sorted(evidence_numbers)),
                f"{field} numeric value differs from evidence",
            )
    return insufficient(claim_id, evidence, f"no explicit {field} evidence found")


def verify_text_field(
    claim_id: str,
    field: str,
    claim_text: str,
    value: str,
    evidence: EvidenceSource,
) -> VerificationResult:
    terms = content_terms(value or claim_text)
    evidence_terms = set(content_terms(evidence.text))
    overlap = [term for term in terms if term in evidence_terms]
    if overlap and len(overlap) >= min(2, len(terms)):
        return VerificationResult(
            claim_id, evidence.source_id, evidence.source_type,
            VERDICT_SUPPORTS, 0.82, quote_around(evidence.text, overlap[0]),
            f"{field} terms overlap evidence",
        )
    field_markers = {
        "collection": ["现藏", "收藏", "藏于"],
        "excavation": ["出土"],
        "inscription": ["铭文", "铸铭"],
        "decoration": ["纹", "饰"],
        "function": ["器", "盛", "用具"],
    }.get(field, [])
    if any(marker in evidence.text for marker in field_markers) and terms:
        return VerificationResult(
            claim_id, evidence.source_id, evidence.source_type,
            VERDICT_INSUFFICIENT, 0.45, "",
            f"{field} evidence exists but does not support the claim value",
        )
    return insufficient(claim_id, evidence, f"no explicit {field} support found")


def verify_missing_info(
    claim_id: str,
    field: str,
    claim_text: str,
    evidence: EvidenceSource,
) -> VerificationResult:
    missing_topic_terms = content_terms(claim_text)
    evidence_terms = set(content_terms(evidence.text))
    overlap = [term for term in missing_topic_terms if term in evidence_terms]
    if any(term in evidence.text for term in ("价格", "作者", "修复", "展览", "估价", "工匠")):
        return VerificationResult(
            claim_id, evidence.source_id, evidence.source_type,
            VERDICT_CONTRADICTS, 0.7, "",
            "evidence appears to contain the information claimed missing",
        )
    if overlap:
        return VerificationResult(
            claim_id, evidence.source_id, evidence.source_type,
            VERDICT_PARTIAL, 0.55, quote_around(evidence.text, overlap[0]),
            "evidence mentions related entity but not the missing information",
        )
    return VerificationResult(
        claim_id, evidence.source_id, evidence.source_type,
        VERDICT_SUPPORTS, 0.65, "",
        "evidence does not contain the requested missing information",
    )


def verify_general(claim_id: str, claim_text: str, evidence: EvidenceSource) -> VerificationResult:
    terms = content_terms(claim_text)
    evidence_terms = set(content_terms(evidence.text))
    overlap = [term for term in terms if term in evidence_terms]
    if overlap and len(overlap) >= min(3, len(terms)):
        return VerificationResult(
            claim_id, evidence.source_id, evidence.source_type,
            VERDICT_SUPPORTS, 0.72, quote_around(evidence.text, overlap[0]),
            "general claim has sufficient lexical overlap",
        )
    if period_conflict(claim_text, evidence.text):
        return VerificationResult(
            claim_id, evidence.source_id, evidence.source_type,
            VERDICT_CONTRADICTS, 0.78, "",
            "general claim contains period conflict",
        )
    return insufficient(claim_id, evidence, "insufficient evidence for general claim")


def insufficient(claim_id: str, evidence: EvidenceSource, reason: str) -> VerificationResult:
    return VerificationResult(
        claim_id,
        evidence.source_id,
        evidence.source_type,
        VERDICT_INSUFFICIENT,
        0.35,
        "",
        reason,
    )


def extract_periods(text: str) -> List[str]:
    return [term for term in PERIOD_TERMS if term in text]


def period_conflict(claim_text: str, evidence_text: str) -> bool:
    claim_periods = set(extract_periods(claim_text))
    evidence_periods = set(extract_periods(evidence_text))
    return bool(claim_periods and evidence_periods and claim_periods.isdisjoint(evidence_periods))


def extract_numbers(text: str) -> List[str]:
    return re.findall(r"\d+(?:\.\d+)?", text)


def content_terms(text: str) -> List[str]:
    terms = re.findall(r"《[^》]+》|[\u4e00-\u9fff]{2,}|\d+(?:\.\d+)?", text)
    stop = {"根据", "知识库", "用户", "回答", "信息", "记载", "介绍", "可以", "没有", "未记载"}
    return [term.strip("《》") for term in terms if term.strip("《》") not in stop]


def quote_around(text: str, value: str, window: int = 40) -> str:
    if not value:
        return ""
    index = text.find(value)
    if index < 0:
        return ""
    return text[max(0, index - window): index + len(value) + window]
