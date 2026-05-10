import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from bronze.bronze_processor import BronzeDataProcessor


CURATABLE_SOURCE_TYPES = {"agent_inference", "memory_derived"}
APPROVED = "approved"
NEEDS_REVIEW = "needs_human_review"
REJECTED = "rejected"
PERIOD_TERMS = [
    "夏代晚期",
    "夏代早期",
    "夏代",
    "商代早期",
    "商代中期",
    "商代晚期",
    "商代",
    "西周早期",
    "西周中期",
    "西周晚期",
    "西周",
    "春秋早期",
    "春秋中期",
    "春秋晚期",
    "春秋时期",
    "春秋",
    "战国早期",
    "战国中期",
    "战国晚期",
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


@dataclass
class AtomicFact:
    claim_id: str
    memory_id: str
    kb_id: str
    entity_id: str
    entity_name: str
    field: str
    value: str
    normalized_value: str
    claim_text: str
    evidence_text: str = ""
    support_type: str = "unsupported"
    confidence: float = 0.0
    conflict_status: str = "unchecked"
    decision: str = NEEDS_REVIEW
    reason: str = ""


class CuratedKnowledgeStore:
    """Append-only verified derived knowledge store.

    bronze_items.json remains immutable. This store starts empty and receives
    only facts approved by the curation pipeline or later human review.
    """

    def __init__(self, path: str = "curated_bronze_knowledge.sqlite3") -> None:
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS curation_runs (
                run_id TEXT PRIMARY KEY,
                architecture TEXT NOT NULL,
                source_metadata_db TEXT NOT NULL,
                base_kb_file TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS curated_facts (
                fact_id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                normalized_value TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(kb_id, field, normalized_value)
            );

            CREATE TABLE IF NOT EXISTS curated_fact_sources (
                source_id TEXT PRIMARY KEY,
                fact_id TEXT NOT NULL,
                source_memory_id TEXT NOT NULL,
                source_turn_id TEXT,
                source_agent TEXT,
                base_kb_id TEXT NOT NULL,
                base_kb_field TEXT NOT NULL,
                base_evidence_text TEXT NOT NULL,
                support_type TEXT NOT NULL,
                curation_run_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS curation_decisions (
                decision_id TEXT PRIMARY KEY,
                curation_run_id TEXT NOT NULL,
                candidate_memory_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                kb_id TEXT NOT NULL,
                field TEXT NOT NULL,
                candidate_value TEXT NOT NULL,
                normalized_value TEXT NOT NULL,
                base_evidence_text TEXT,
                support_type TEXT NOT NULL,
                conflict_status TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence REAL NOT NULL,
                decided_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS human_review_queue (
                review_id TEXT PRIMARY KEY,
                curation_run_id TEXT NOT NULL,
                candidate_memory_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                kb_id TEXT,
                field TEXT,
                candidate_value TEXT NOT NULL,
                evidence TEXT NOT NULL DEFAULT '{}',
                conflict_summary TEXT NOT NULL,
                suggested_decision TEXT NOT NULL,
                status TEXT NOT NULL,
                human_decision TEXT,
                human_notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_curated_facts_kb ON curated_facts(kb_id);
            CREATE INDEX IF NOT EXISTS idx_decisions_memory ON curation_decisions(candidate_memory_id);
            CREATE INDEX IF NOT EXISTS idx_review_status ON human_review_queue(status);
            """
        )
        self.conn.commit()

    def start_run(self, *, architecture: str, source_metadata_db: str, base_kb_file: str) -> str:
        run_id = f"cur_{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            """
            INSERT INTO curation_runs (
                run_id, architecture, source_metadata_db, base_kb_file,
                started_at, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, architecture, source_metadata_db, base_kb_file, now_iso(), "running"),
        )
        self.conn.commit()
        return run_id

    def finish_run(self, run_id: str, *, status: str, summary: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            UPDATE curation_runs
            SET finished_at = ?, status = ?, summary = ?
            WHERE run_id = ?
            """,
            (now_iso(), status, json.dumps(summary, ensure_ascii=False), run_id),
        )
        self.conn.commit()

    def record_decision(self, run_id: str, fact: AtomicFact, *, memory: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO curation_decisions (
                decision_id, curation_run_id, candidate_memory_id, claim_id,
                kb_id, field, candidate_value, normalized_value,
                base_evidence_text, support_type, conflict_status,
                decision, reason, confidence, decided_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"dec_{uuid.uuid4().hex[:12]}",
                run_id,
                fact.memory_id,
                fact.claim_id,
                fact.kb_id,
                fact.field,
                fact.value,
                fact.normalized_value,
                fact.evidence_text,
                fact.support_type,
                fact.conflict_status,
                fact.decision,
                fact.reason,
                fact.confidence,
                "CurationRuleEngine",
                now_iso(),
            ),
        )
        if fact.decision == APPROVED:
            self.upsert_curated_fact(run_id, fact, memory=memory)
        elif fact.decision == NEEDS_REVIEW:
            self.enqueue_review(run_id, fact)
        self.conn.commit()

    def upsert_curated_fact(self, run_id: str, fact: AtomicFact, *, memory: Dict[str, Any]) -> str:
        row = self.conn.execute(
            """
            SELECT fact_id FROM curated_facts
            WHERE kb_id = ? AND field = ? AND normalized_value = ?
            """,
            (fact.kb_id, fact.field, fact.normalized_value),
        ).fetchone()
        if row:
            fact_id = str(row["fact_id"])
            self.conn.execute(
                "UPDATE curated_facts SET updated_at = ? WHERE fact_id = ?",
                (now_iso(), fact_id),
            )
        else:
            fact_id = f"cf_{uuid.uuid4().hex[:12]}"
            self.conn.execute(
                """
                INSERT INTO curated_facts (
                    fact_id, kb_id, entity_id, entity_name, field, value,
                    normalized_value, confidence, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact_id,
                    fact.kb_id,
                    fact.entity_id,
                    fact.entity_name,
                    fact.field,
                    fact.value,
                    fact.normalized_value,
                    fact.confidence,
                    "approved",
                    now_iso(),
                    now_iso(),
                ),
            )

        self.conn.execute(
            """
            INSERT INTO curated_fact_sources (
                source_id, fact_id, source_memory_id, source_turn_id,
                source_agent, base_kb_id, base_kb_field, base_evidence_text,
                support_type, curation_run_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"cfs_{uuid.uuid4().hex[:12]}",
                fact_id,
                fact.memory_id,
                memory.get("created_turn"),
                memory.get("created_by"),
                fact.kb_id,
                fact.field,
                fact.evidence_text,
                fact.support_type,
                run_id,
                now_iso(),
            ),
        )
        return fact_id

    def enqueue_review(self, run_id: str, fact: AtomicFact) -> None:
        self.conn.execute(
            """
            INSERT INTO human_review_queue (
                review_id, curation_run_id, candidate_memory_id, claim_id,
                kb_id, field, candidate_value, evidence, conflict_summary,
                suggested_decision, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"rev_{uuid.uuid4().hex[:12]}",
                run_id,
                fact.memory_id,
                fact.claim_id,
                fact.kb_id,
                fact.field,
                fact.value,
                json.dumps(
                    {
                        "base_evidence_text": fact.evidence_text,
                        "support_type": fact.support_type,
                        "confidence": fact.confidence,
                    },
                    ensure_ascii=False,
                ),
                fact.reason,
                fact.decision,
                "open",
                now_iso(),
                now_iso(),
            ),
        )

    def approved_facts(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM curated_facts
            WHERE status = 'approved'
            ORDER BY kb_id ASC, field ASC, created_at ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def export_approved_facts(self, path: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "source": str(self.path),
                    "facts": self.approved_facts(),
                },
                file,
                ensure_ascii=False,
                indent=2,
            )

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()


class MemoryCurationManager:
    """Batch pipeline for promoting verified memories into a derived KB."""

    def __init__(
        self,
        *,
        metadata_db: str,
        base_kb_file: str = "bronze_items.json",
        curated_kb_path: str = "curated_bronze_knowledge.sqlite3",
        architecture: str = "unknown",
    ) -> None:
        self.metadata_db = Path(metadata_db)
        self.base_kb_file = base_kb_file
        self.architecture = architecture
        self.memory_conn = sqlite3.connect(self.metadata_db)
        self.memory_conn.row_factory = sqlite3.Row
        self.processor = BronzeDataProcessor(base_kb_file)
        self.items_by_id = {
            str(item.get("id")): item
            for item in self.processor.data
            if item.get("id") is not None
        }
        self.items_by_name = {
            str(item.get("name", "")).strip(): item
            for item in self.processor.data
            if str(item.get("name", "")).strip()
        }
        self.store = CuratedKnowledgeStore(curated_kb_path)

    def run(
        self,
        *,
        limit: int = 0,
        include_suspected: bool = True,
        review_output: Optional[str] = None,
    ) -> Dict[str, Any]:
        run_id = self.store.start_run(
            architecture=self.architecture,
            source_metadata_db=str(self.metadata_db),
            base_kb_file=self.base_kb_file,
        )
        candidates = self.select_candidates(limit=limit, include_suspected=include_suspected)
        summary = {
            "run_id": run_id,
            "candidate_count": len(candidates),
            "atomic_fact_count": 0,
            "approved_count": 0,
            "needs_human_review_count": 0,
            "rejected_count": 0,
            "candidates": [],
        }
        try:
            for memory in candidates:
                facts = self.extract_atomic_facts(memory)
                summary["atomic_fact_count"] += len(facts)
                candidate_report = {
                    "memory_id": memory["memory_id"],
                    "source_type": memory["source_type"],
                    "created_by": memory["created_by"],
                    "created_turn": memory["created_turn"],
                    "content": memory["content"],
                    "facts": [],
                }
                for fact in facts:
                    self.ground_and_decide(fact)
                    self.store.record_decision(run_id, fact, memory=memory)
                    self.increment_decision_count(summary, fact.decision)
                    candidate_report["facts"].append(fact.__dict__)
                if not facts:
                    review_fact = self.unsupported_memory_fact(memory)
                    self.store.record_decision(run_id, review_fact, memory=memory)
                    self.increment_decision_count(summary, review_fact.decision)
                    candidate_report["facts"].append(review_fact.__dict__)
                summary["candidates"].append(candidate_report)

            self.store.finish_run(run_id, status="completed", summary=summary)
            if review_output:
                self.export_review_queue(review_output, run_id=run_id)
            return summary
        except Exception:
            self.store.finish_run(run_id, status="failed", summary=summary)
            raise

    def select_candidates(self, *, limit: int, include_suspected: bool) -> List[Dict[str, Any]]:
        contamination_clause = (
            "AND contamination_status IN ('clean', 'suspected', 'unknown')"
            if include_suspected
            else "AND contamination_status = 'clean'"
        )
        sql = f"""
            SELECT *
            FROM memories
            WHERE source_type IN ({','.join('?' for _ in CURATABLE_SOURCE_TYPES)})
              {contamination_clause}
            ORDER BY created_at ASC
        """
        params: List[Any] = sorted(CURATABLE_SOURCE_TYPES)
        if limit > 0:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self.memory_conn.execute(sql, params).fetchall()
        return [self.decode_memory_row(dict(row)) for row in rows]

    def increment_decision_count(self, summary: Dict[str, Any], decision: str) -> None:
        key = f"{decision}_count"
        summary[key] = int(summary.get(key, 0)) + 1

    def decode_memory_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("source_ids", "derived_from", "metadata"):
            row[key] = load_json(row.get(key), [] if key != "metadata" else {})
        return row

    def extract_atomic_facts(self, memory: Dict[str, Any]) -> List[AtomicFact]:
        content = str(memory.get("content", ""))
        item = self.resolve_item(memory)
        if not item:
            return []

        item_id = str(item.get("id"))
        kb_id = f"KB_{item_id}"
        name = str(item.get("name", "")).strip()
        base_fields = self.base_fields(item)
        facts: List[AtomicFact] = []

        for field, base_value in base_fields.items():
            if not base_value:
                continue
            for value in self.extract_values_for_field(field, base_value, content):
                facts.append(
                    AtomicFact(
                        claim_id=f"claim_{uuid.uuid4().hex[:12]}",
                        memory_id=str(memory["memory_id"]),
                        kb_id=kb_id,
                        entity_id=item_id,
                        entity_name=name,
                        field=field,
                        value=value,
                        normalized_value=normalize_value(value),
                        claim_text=f"{name}.{field} = {value}",
                    )
                )
        return self.dedupe_facts(facts)

    def resolve_item(self, memory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        content = str(memory.get("content", ""))
        for source_id in memory.get("source_ids", []):
            match = re.search(r"KB_(\d+)", str(source_id))
            if match and match.group(1) in self.items_by_id:
                return self.items_by_id[match.group(1)]
        match = re.search(r"(?:KB_|ID\s*[:：]?\s*)(\d{5,})", content)
        if match and match.group(1) in self.items_by_id:
            return self.items_by_id[match.group(1)]
        matches = [
            (name, item)
            for name, item in self.items_by_name.items()
            if name and name in content
        ]
        if matches:
            return max(matches, key=lambda pair: len(pair[0]))[1]
        return None

    def base_fields(self, item: Dict[str, Any]) -> Dict[str, str]:
        summary = str(item.get("summary", "")).strip()
        detail = str(item.get("detail", "")).strip()
        return {
            "name": str(item.get("name", "")).strip(),
            "category": str(item.get("category", "")).strip(),
            "period": extract_period(summary + " " + detail),
            "function": extract_function(summary),
            "dimensions": "；".join(extract_measurements(detail, include_weight=False)),
            "weight": "；".join(extract_weights(detail)),
            "excavation": extract_excavation(detail),
            "collection": extract_collection(detail),
            "inscription": extract_inscription(detail),
            "decoration": extract_decoration(detail),
        }

    def extract_values_for_field(self, field: str, base_value: str, content: str) -> List[str]:
        values: List[str] = []
        if field in {"name", "category", "period", "function"}:
            if field == "period":
                return extract_periods(content)
            if base_value and base_value in content:
                values.append(base_value)
            return values
        if field == "dimensions":
            return extract_measurements(content, include_weight=False)
        if field == "weight":
            return extract_weights(content)
        if field in {"excavation", "collection", "inscription", "decoration"}:
            if base_value and base_value in content:
                values.append(base_value)
            else:
                for sentence in split_sentences(base_value):
                    if sentence and sentence in content:
                        values.append(sentence)
            return values
        if base_value and base_value in content:
            values.append(base_value)
        return values

    def dedupe_facts(self, facts: Sequence[AtomicFact]) -> List[AtomicFact]:
        seen = set()
        result = []
        for fact in facts:
            key = (fact.kb_id, fact.field, fact.normalized_value)
            if key in seen:
                continue
            seen.add(key)
            result.append(fact)
        return result

    def ground_and_decide(self, fact: AtomicFact) -> None:
        item = self.items_by_id.get(fact.entity_id)
        base_value = self.base_fields(item).get(fact.field, "") if item else ""
        base_text = artifact_text(item) if item else ""

        if fact.value and fact.value in base_value:
            fact.support_type = "exact_match"
            fact.evidence_text = base_value
            fact.confidence = 0.98
            fact.conflict_status = "same"
            fact.decision = APPROVED
            fact.reason = "candidate value exactly matches immutable base KB field"
        elif fact.value and fact.value in base_text:
            fact.support_type = "entailed"
            fact.evidence_text = evidence_sentence(base_text, fact.value)
            fact.confidence = 0.88
            fact.conflict_status = "compatible_extension"
            fact.decision = APPROVED
            fact.reason = "candidate value appears in immutable base KB evidence text"
        elif base_value:
            fact.support_type = "conflicting_or_unsupported"
            fact.evidence_text = base_value
            fact.confidence = 0.45
            fact.conflict_status = "field_conflict_with_base_kb"
            fact.decision = NEEDS_REVIEW
            fact.reason = "candidate value differs from the immutable base KB field; base KB takes precedence"
        else:
            fact.support_type = "unsupported"
            fact.evidence_text = base_value
            fact.confidence = 0.35
            fact.conflict_status = "unsupported"
            fact.decision = NEEDS_REVIEW
            fact.reason = "candidate value could not be grounded in immutable base KB"

    def unsupported_memory_fact(self, memory: Dict[str, Any]) -> AtomicFact:
        return AtomicFact(
            claim_id=f"claim_{uuid.uuid4().hex[:12]}",
            memory_id=str(memory["memory_id"]),
            kb_id="",
            entity_id="",
            entity_name="",
            field="unresolved_memory",
            value=str(memory.get("content", "")),
            normalized_value=normalize_value(str(memory.get("content", ""))),
            claim_text=str(memory.get("content", "")),
            support_type="unsupported",
            confidence=0.2,
            conflict_status="unresolved_entity",
            decision=NEEDS_REVIEW,
            reason="no matching base KB entity was found",
        )

    def export_review_queue(self, path: str, *, run_id: str) -> None:
        rows = self.store.conn.execute(
            """
            SELECT *
            FROM human_review_queue
            WHERE curation_run_id = ?
            ORDER BY created_at ASC
            """,
            (run_id,),
        ).fetchall()
        review_items = [dict(row) for row in rows]
        for item in review_items:
            item["evidence"] = load_json(item.get("evidence"), {})
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                {
                    "run_id": run_id,
                    "review_items": review_items,
                    "instructions": {
                        "human_decision": "set to approved, rejected, or needs_more_evidence",
                        "human_notes": "explain the decision or correction",
                    },
                },
                file,
                ensure_ascii=False,
                indent=2,
            )

    def close(self) -> None:
        self.memory_conn.close()
        self.store.close()


def extract_period(text: str) -> str:
    periods = extract_periods(text)
    if periods:
        return periods[0]
    return ""


def extract_periods(text: str) -> List[str]:
    return [term for term in PERIOD_TERMS if term in text]


def extract_function(summary: str) -> str:
    match = re.search(r"(乐器|兵器|照容用具|[^，。；\s]{1,12}器)", summary)
    return match.group(1) if match else ""


def extract_measurements(text: str, *, include_weight: bool) -> List[str]:
    pattern = r"(?:高|长|宽|口径|底径|腹深|直径|通高|厚)\s*[\d.]+\s*(?:厘米|cm|CM)"
    values = re.findall(pattern, text)
    if include_weight:
        values.extend(extract_weights(text))
    return values


def extract_weights(text: str) -> List[str]:
    return re.findall(r"重\s*[\d.]+\s*(?:千克|克|公斤|kg|KG)", text)


def extract_excavation(text: str) -> str:
    match = re.search(r"(\d{4}年[^。；]*出土)", text)
    return match.group(1) if match else ""


def extract_collection(text: str) -> str:
    match = re.search(r"(?:现藏|藏于)([^。；]+)", text)
    return match.group(0) if match else ""


def extract_inscription(text: str) -> str:
    sentences = [sentence for sentence in split_sentences(text) if "铭文" in sentence]
    return "。".join(sentences)


def extract_decoration(text: str) -> str:
    sentences = [
        sentence
        for sentence in split_sentences(text)
        if any(term in sentence for term in ("纹", "饰", "钮", "耳", "足"))
    ]
    return "。".join(sentences[:3])


def split_sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"[。；\n]", text) if part.strip()]


def evidence_sentence(text: str, value: str) -> str:
    for sentence in split_sentences(text):
        if value in sentence:
            return sentence
    return value


def artifact_text(item: Optional[Dict[str, Any]]) -> str:
    if not item:
        return ""
    return " ".join(
        str(item.get(key, ""))
        for key in ("id", "name", "category", "summary", "detail")
    )


def normalize_value(value: str) -> str:
    return re.sub(r"\s+", "", str(value)).replace("cm", "厘米").replace("CM", "厘米")


def load_json(value: Any, default: Any) -> Any:
    if not isinstance(value, str) or not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
