import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from bronze.bronze_memory import ArchitectureMemory
from bronze.bronze_processor import BronzeDataProcessor
from vector_db import VectorDatabase


PERIOD_TERMS = [
    "夏代晚期",
    "夏代早期",
    "夏代",
    "商代早期",
    "商代晚期",
    "商代中期",
    "商代",
    "西周早期",
    "西周晚期",
    "西周中期",
    "西周",
    "春秋早期",
    "春秋晚期",
    "春秋中期",
    "春秋时期",
    "春秋",
    "战国早期",
    "战国晚期",
    "战国中期",
    "战国时期",
    "战国",
    "秦代",
    "西汉",
    "东汉",
    "汉代",
    "唐代",
    "宋代",
    "元代",
    "明代",
    "清代",
]


AUTO_CORRECT_THRESHOLD = 0.86
MANUAL_REVIEW_THRESHOLD = 0.55


@dataclass
class AuditResult:
    memory_id: str
    verdict: str
    confidence: float
    reasons: List[str]
    correction: str = ""
    evidence: Optional[Dict[str, Any]] = None


class MemoryAuditor:
    """Audit committed memories against the bronze artifact evidence base."""

    def __init__(
        self,
        memory: ArchitectureMemory,
        data_file: str = "bronze_items.json",
        vector_db: Optional[VectorDatabase] = None,
    ) -> None:
        self.memory = memory
        self.processor = BronzeDataProcessor(data_file)
        self.vector_db = vector_db
        self.artifacts = self.processor.data
        self.artifacts_by_name = {
            str(item.get("name", "")).strip(): item
            for item in self.artifacts
            if str(item.get("name", "")).strip()
        }

    def audit(
        self,
        *,
        auto_correct: bool = True,
        review_file: Optional[str] = None,
        rebuild_vector_db: bool = True,
    ) -> List[AuditResult]:
        results = []
        review_items = []

        for item in self.memory.get_active_committed_memories():
            result = self.audit_memory(item)
            results.append(result)

            if result.verdict == "auto_correctable" and auto_correct:
                self.apply_correction(item, result)
            elif result.verdict == "needs_review":
                review_items.append(self.to_review_item(item, result))

        if review_file:
            self.export_review_file(review_items, review_file)

        if auto_correct and rebuild_vector_db and self.vector_db:
            self.rebuild_vector_database()

        return results

    def audit_memory(self, memory_item: Dict[str, Any]) -> AuditResult:
        memory_id = str(memory_item.get("memory_id", ""))
        content = str(memory_item.get("content", "")).strip()
        if not content:
            return AuditResult(memory_id, "needs_review", 0.6, ["empty committed memory"])

        evidence = self.find_artifact_evidence(content)
        if not evidence:
            return AuditResult(
                memory_id,
                "needs_review",
                0.58,
                ["no exact artifact name from the bronze evidence base was found"],
            )

        reasons = []
        correction_parts = []
        conflict_score = 0.0

        artifact = evidence["artifact"]
        name = evidence["name"]
        period_conflict = self.detect_period_conflict(content, self.period_evidence_text(artifact))
        if period_conflict:
            wrong_terms, evidence_terms = period_conflict
            reasons.append(
                "period conflict: memory contains "
                + ", ".join(wrong_terms)
                + " but evidence supports "
                + ", ".join(evidence_terms)
            )
            conflict_score += 0.48
            correction_parts.append(
                f"{name}的年代应以证据库为准：{self.short_fact(artifact)}"
            )

        category_conflict = self.detect_category_conflict(content, artifact)
        if category_conflict:
            wrong_terms, evidence_category = category_conflict
            reasons.append(
                "category conflict: memory contains "
                + ", ".join(wrong_terms)
                + f" but evidence category is {evidence_category}"
            )
            conflict_score += 0.34
            correction_parts.append(f"{name}的器类是{evidence_category}。")

        if "不是" in content or "错误前提" in content or "应先纠正" in content:
            conflict_score -= 0.18

        if not reasons:
            return AuditResult(memory_id, "supported", 0.92, ["supported by artifact evidence"], evidence=evidence)

        confidence = min(0.98, max(0.0, conflict_score + 0.38))
        correction = " ".join(correction_parts) or f"{name}的信息应以证据库为准：{self.short_fact(artifact)}"

        if confidence >= AUTO_CORRECT_THRESHOLD:
            verdict = "auto_correctable"
        elif confidence >= MANUAL_REVIEW_THRESHOLD:
            verdict = "needs_review"
        else:
            verdict = "supported"
        return AuditResult(memory_id, verdict, confidence, reasons, correction, evidence)

    def apply_correction(self, memory_item: Dict[str, Any], result: AuditResult) -> str:
        old_memory_id = str(memory_item.get("memory_id", ""))
        self.memory.deactivate_committed_memory(
            old_memory_id,
            reason="auto memory audit detected factual conflict",
        )
        source_candidates = list(memory_item.get("source_candidates", []))
        return self.memory.commit_memory(
            result.correction,
            memory_type="correction",
            source_candidates=source_candidates,
            corrects=[old_memory_id],
            conversation_id=memory_item.get("conversation_id"),
            metadata={
                "audit_confidence": result.confidence,
                "audit_reasons": result.reasons,
                "audit_evidence": result.evidence,
            },
            add_to_vector=False,
        )

    def rebuild_vector_database(self) -> None:
        if not self.vector_db:
            return
        self.vector_db.clear()
        for text in self.processor.generate_text_representations():
            self.vector_db.add_text(text)
        for item in self.memory.get_active_committed_memories():
            self.vector_db.add_text(
                f"Committed memory\n"
                f"Memory ID: {item.get('memory_id', '')}\n"
                f"Memory type: {item.get('memory_type', '')}\n"
                f"Content: {item.get('content', '')}"
            )
        self.vector_db.save()

    def export_review_file(self, review_items: List[Dict[str, Any]], review_file: str) -> None:
        output_path = Path(review_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "review_items": review_items,
                    "instructions": {
                        "human_label": "set to supported, hallucination, or correction_needed",
                        "human_correction": "fill when the memory should be edited",
                    },
                },
                file,
                ensure_ascii=False,
                indent=2,
            )

    def to_review_item(self, memory_item: Dict[str, Any], result: AuditResult) -> Dict[str, Any]:
        return {
            "memory_id": memory_item.get("memory_id"),
            "conversation_id": memory_item.get("conversation_id"),
            "content": memory_item.get("content"),
            "memory_type": memory_item.get("memory_type"),
            "status": memory_item.get("status"),
            "audit_confidence": result.confidence,
            "audit_reasons": result.reasons,
            "suggested_correction": result.correction,
            "evidence": result.evidence,
            "human_label": "",
            "human_correction": "",
            "human_notes": "",
        }

    def apply_human_review(self, review_file: str, *, rebuild_vector_db: bool = True) -> Dict[str, int]:
        with Path(review_file).open("r", encoding="utf-8") as file:
            data = json.load(file)
        counts = {"supported": 0, "corrected": 0, "rejected": 0}

        for item in data.get("review_items", []):
            label = str(item.get("human_label", "")).strip()
            memory_id = str(item.get("memory_id", "")).strip()
            if not label or not memory_id:
                continue
            if label == "supported":
                counts["supported"] += 1
                continue
            if label in {"hallucination", "correction_needed"}:
                self.memory.deactivate_committed_memory(
                    memory_id,
                    reason=f"human review label: {label}",
                )
                correction = str(item.get("human_correction") or item.get("suggested_correction") or "").strip()
                if correction:
                    self.memory.commit_memory(
                        correction,
                        memory_type="correction",
                        source_candidates=[],
                        corrects=[memory_id],
                        conversation_id=item.get("conversation_id"),
                        metadata={"human_notes": item.get("human_notes", "")},
                        add_to_vector=False,
                    )
                    counts["corrected"] += 1
                else:
                    counts["rejected"] += 1

        if rebuild_vector_db and self.vector_db:
            self.rebuild_vector_database()
        return counts

    def find_artifact_evidence(self, content: str) -> Optional[Dict[str, Any]]:
        matches = [
            name for name in self.artifacts_by_name
            if name and name in content
        ]
        if not matches:
            return None
        name = max(matches, key=len)
        artifact = self.artifacts_by_name[name]
        return {
            "name": name,
            "artifact": artifact,
            "summary": artifact.get("summary", ""),
            "detail": artifact.get("detail", ""),
            "category": artifact.get("category", ""),
        }

    def detect_period_conflict(
        self,
        content: str,
        evidence_text: str,
    ) -> Optional[tuple[List[str], List[str]]]:
        content_terms = self.extract_period_terms(content)
        evidence_terms = self.extract_period_terms(evidence_text)
        if not content_terms or not evidence_terms:
            return None
        wrong_terms = [
            term for term in content_terms
            if not self.term_compatible(term, evidence_terms)
        ]
        if not wrong_terms:
            return None
        return wrong_terms, evidence_terms

    def detect_category_conflict(
        self,
        content: str,
        artifact: Dict[str, Any],
    ) -> Optional[tuple[List[str], str]]:
        category = str(artifact.get("category", "")).strip()
        if not category or category in content:
            return None
        category_terms = self.extract_category_terms(content)
        wrong_terms = [term for term in category_terms if term != category]
        if not wrong_terms:
            return None
        return wrong_terms, category

    def extract_period_terms(self, text: str) -> List[str]:
        terms = [term for term in PERIOD_TERMS if term in text]
        return self.remove_subsumed_terms(terms)

    def extract_category_terms(self, text: str) -> List[str]:
        categories = {str(item.get("category", "")).strip() for item in self.artifacts}
        return sorted([term for term in categories if term and term in text], key=len, reverse=True)

    def remove_subsumed_terms(self, terms: Sequence[str]) -> List[str]:
        result = []
        for term in sorted(set(terms), key=len, reverse=True):
            if not any(term != existing and term in existing for existing in result):
                result.append(term)
        return result

    def term_compatible(self, term: str, evidence_terms: Sequence[str]) -> bool:
        return any(term in evidence or evidence in term for evidence in evidence_terms)

    def artifact_text(self, artifact: Dict[str, Any]) -> str:
        return " ".join(
            str(artifact.get(key, ""))
            for key in ("name", "category", "summary", "detail")
        )

    def period_evidence_text(self, artifact: Dict[str, Any]) -> str:
        summary = str(artifact.get("summary", "")).strip()
        if self.extract_period_terms(summary):
            return summary
        return self.artifact_text(artifact)

    def short_fact(self, artifact: Dict[str, Any]) -> str:
        name = str(artifact.get("name", "")).strip()
        category = str(artifact.get("category", "")).strip()
        summary = str(artifact.get("summary", "")).strip()
        detail = str(artifact.get("detail", "")).strip()
        location = self.extract_location(detail)
        parts = [f"{name}是{summary}"]
        if category:
            parts.append(f"器类为{category}。")
        if location:
            parts.append(location)
        return "".join(parts)

    def extract_location(self, text: str) -> str:
        match = re.search(r"(\d{4}年)?([^。；]*出土)", text)
        if not match:
            return ""
        return match.group(0) + "。"
