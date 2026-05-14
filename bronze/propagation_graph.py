import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from bronze.claim_extractor import HybridClaimExtractor
from bronze.claim_verifier import HybridClaimVerifier


NODE_TURN = "Turn"
NODE_QUESTION = "Question"
NODE_ANSWER = "Answer"
NODE_CLAIM = "Claim"
NODE_MEMORY = "Memory"
NODE_KB_ITEM = "KBItem"
NODE_EDITED_KNOWLEDGE = "EditedKnowledge"
NODE_AGENT = "Agent"
NODE_EDITOR = "Editor"


class PropagationGraphStore:
    """SQLite-backed heterogeneous graph for memory hallucination propagation."""

    def __init__(self, path: str = "propagation_graph.sqlite3") -> None:
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS graph_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                label TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS graph_edges_unified (
                edge_id TEXT PRIMARY KEY,
                edge_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                confidence REAL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(edge_type, source_id, target_id)
            );

            CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges_unified(edge_type);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges_unified(source_id);
            CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges_unified(target_id);
            """
        )
        self.conn.commit()

    def upsert_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                node_type = excluded.node_type,
                label = excluded.label,
                payload = excluded.payload
            """,
            (
                node_id,
                node_type,
                label,
                json.dumps(payload or {}, ensure_ascii=False),
                now_iso(),
            ),
        )

    def add_edge(
        self,
        edge_type: str,
        source_id: str,
        target_id: str,
        source_type: str,
        target_type: str,
        *,
        confidence: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        edge_id = stable_id("edge", edge_type, source_id, target_id)
        self.conn.execute(
            """
            INSERT INTO graph_edges_unified (
                edge_id, edge_type, source_id, target_id,
                source_type, target_type, confidence, payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(edge_type, source_id, target_id) DO UPDATE SET
                confidence = COALESCE(excluded.confidence, graph_edges_unified.confidence),
                payload = excluded.payload
            """,
            (
                edge_id,
                edge_type,
                source_id,
                target_id,
                source_type,
                target_type,
                confidence,
                json.dumps(payload or {}, ensure_ascii=False),
                now_iso(),
            ),
        )

    def summary(self) -> Dict[str, Any]:
        node_rows = self.conn.execute(
            "SELECT node_type, COUNT(*) AS count FROM graph_nodes GROUP BY node_type"
        ).fetchall()
        edge_rows = self.conn.execute(
            "SELECT edge_type, COUNT(*) AS count FROM graph_edges_unified GROUP BY edge_type"
        ).fetchall()
        return {
            "graph_db": str(self.path),
            "nodes": {row["node_type"]: int(row["count"]) for row in node_rows},
            "edges": {row["edge_type"]: int(row["count"]) for row in edge_rows},
        }

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()


class PropagationGraphBuilder:
    def __init__(
        self,
        *,
        graph_db: str = "propagation_graph.sqlite3",
        metadata_db: str = "vector_db_bronze_peer/metadata.sqlite3",
        curated_db: str = "",
        curation_report: str = "",
    ) -> None:
        self.store = PropagationGraphStore(graph_db)
        self.metadata_db = Path(metadata_db)
        self.curated_db = Path(curated_db) if curated_db else None
        self.curation_report = Path(curation_report) if curation_report else None
        self.claim_extractor = HybridClaimExtractor()
        self.claim_verifier = HybridClaimVerifier()

    def build_from_results(self, result_files: Sequence[str]) -> Dict[str, Any]:
        self.import_metadata_db()
        for path in result_files:
            self.import_result_file(path)
        if self.curated_db and self.curated_db.exists():
            self.import_curated_db()
        if self.curation_report and self.curation_report.exists():
            self.import_curation_report()
        self.infer_contamination_and_repairs()
        self.store.conn.commit()
        return self.store.summary()

    def import_metadata_db(self) -> None:
        if not self.metadata_db.exists():
            return
        conn = sqlite3.connect(self.metadata_db)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT * FROM memories").fetchall():
            memory = decode_sqlite_row(row)
            memory_id = str(memory.get("memory_id"))
            label = memory_label(memory)
            self.store.upsert_node(
                node_id_for_memory(memory_id),
                node_type=NODE_MEMORY,
                label=label,
                payload=memory,
            )
            for source_id in memory.get("source_ids", []):
                if str(source_id).startswith("KB_"):
                    kb_node = node_id_for_kb(str(source_id))
                    self.store.upsert_node(kb_node, NODE_KB_ITEM, str(source_id), {"kb_id": source_id})
                    self.store.add_edge(
                        "supports",
                        kb_node,
                        node_id_for_memory(memory_id),
                        NODE_KB_ITEM,
                        NODE_MEMORY,
                        confidence=memory.get("confidence"),
                        payload={"reason": "memory source_ids references KB item"},
                    )
            for parent in memory.get("derived_from", []):
                self.store.add_edge(
                    "derived_from",
                    node_id_for_memory(memory_id),
                    node_id_for_memory(str(parent)),
                    NODE_MEMORY,
                    NODE_MEMORY,
                    confidence=memory.get("confidence"),
                    payload={"created_turn": memory.get("created_turn")},
                )

        for row in conn.execute("SELECT * FROM graph_edges").fetchall():
            edge = decode_sqlite_row(row)
            source_type = normalize_node_type(str(edge.get("source_type")))
            target_type = normalize_node_type(str(edge.get("target_type")))
            source_id = normalize_node_id(str(edge.get("source_type")), str(edge.get("source_id")))
            target_id = normalize_node_id(str(edge.get("target_type")), str(edge.get("target_id")))
            self.store.upsert_node(source_id, source_type, source_id, {"imported_from": "metadata.graph_edges"})
            self.store.upsert_node(target_id, target_type, target_id, {"imported_from": "metadata.graph_edges"})
            self.store.add_edge(
                str(edge.get("edge_type")),
                source_id,
                target_id,
                source_type,
                target_type,
                confidence=edge.get("confidence"),
                payload=edge,
            )
        conn.close()

    def import_result_file(self, path: str) -> None:
        result_path = Path(path)
        if not result_path.exists():
            return
        data = load_json(result_path)
        dataset_payload = {
            "source_file": str(result_path),
            "architecture": data.get("architecture"),
            "curated_kb": data.get("curated_kb"),
            "generated_at": data.get("generated_at"),
        }
        for result in data.get("results", []):
            test_id = str(result.get("test_id", "unknown"))
            questioner_id = node_id_for_agent("QuestionerAgent")
            self.store.upsert_node(questioner_id, NODE_AGENT, "QuestionerAgent", {})
            for turn_log in result.get("turn_logs", []):
                self.import_turn_log(test_id, turn_log, dataset_payload)

    def import_turn_log(self, test_id: str, turn_log: Dict[str, Any], dataset_payload: Dict[str, Any]) -> None:
        turn_id = str(turn_log.get("turn_id") or f"{test_id}_turn_{turn_log.get('turn_index', 0)}")
        turn_node = node_id_for_turn(turn_id)
        question_id = node_id_for_question(turn_id)
        answer_id = node_id_for_answer(turn_id)
        question = str(turn_log.get("question", ""))
        answer = str(turn_log.get("final_answer", ""))
        answer_agent = str(turn_log.get("final_answer_agent") or "AnswerAgent")
        answer_agent_id = node_id_for_agent(answer_agent)
        questioner_id = node_id_for_agent("QuestionerAgent")

        self.store.upsert_node(
            turn_node,
            NODE_TURN,
            turn_id,
            {"test_id": test_id, "turn_index": turn_log.get("turn_index"), **dataset_payload},
        )
        self.store.upsert_node(question_id, NODE_QUESTION, trim_label(question), {"text": question, "turn_id": turn_id})
        self.store.upsert_node(answer_id, NODE_ANSWER, trim_label(answer), {"text": answer, "turn_id": turn_id, "agent": answer_agent})
        self.store.upsert_node(answer_agent_id, NODE_AGENT, answer_agent, {})

        self.store.add_edge("contains", turn_node, question_id, NODE_TURN, NODE_QUESTION)
        self.store.add_edge("contains", turn_node, answer_id, NODE_TURN, NODE_ANSWER)
        self.store.add_edge("asks", questioner_id, question_id, NODE_AGENT, NODE_QUESTION)
        self.store.add_edge("answers", answer_agent_id, answer_id, NODE_AGENT, NODE_ANSWER)

        for memory_id in turn_log.get("retrieval", {}).get("retrieved_memory_ids", []):
            self.store.add_edge(
                "retrieves",
                answer_agent_id,
                node_id_for_memory(str(memory_id)),
                NODE_AGENT,
                NODE_MEMORY,
                payload={"turn_id": turn_id, "question_id": question_id},
            )
        for memory_id in turn_log.get("usage", {}).get("used_memory_ids", []):
            self.store.add_edge(
                "uses",
                answer_agent_id,
                node_id_for_memory(str(memory_id)),
                NODE_AGENT,
                NODE_MEMORY,
                payload={"turn_id": turn_id, "answer_id": answer_id},
            )
            self.store.add_edge(
                "supports",
                node_id_for_memory(str(memory_id)),
                answer_id,
                NODE_MEMORY,
                NODE_ANSWER,
                payload={"relation": "used memory supports answer"},
            )
        for kb_id in turn_log.get("retrieval", {}).get("retrieved_kb_ids", []):
            self.store.add_edge(
                "retrieves",
                answer_agent_id,
                node_id_for_kb(str(kb_id)),
                NODE_AGENT,
                NODE_KB_ITEM,
                payload={"turn_id": turn_id, "question_id": question_id},
            )

        claims = self.claim_extractor.extract(
            answer_id=answer_id,
            answer_text=answer,
            question=question,
            target_item_ids=[],
        )
        for claim in claims:
            claim_node = node_id_for_claim(claim["claim_id"])
            self.store.upsert_node(claim_node, NODE_CLAIM, trim_label(claim["claim_text"]), claim)
            self.store.add_edge("extracts", answer_id, claim_node, NODE_ANSWER, NODE_CLAIM)
            self.link_claim_evidence(claim_node, claim, turn_log)

        for fact in turn_log.get("curated_knowledge", {}).get("curated_facts", []):
            fact_node = node_id_for_edited_knowledge(str(fact.get("fact_id")))
            self.store.upsert_node(
                fact_node,
                NODE_EDITED_KNOWLEDGE,
                f"{fact.get('kb_id')} {fact.get('field')}={fact.get('value')}",
                fact,
            )
            self.store.add_edge(
                "retrieves",
                answer_agent_id,
                fact_node,
                NODE_AGENT,
                NODE_EDITED_KNOWLEDGE,
                payload={"turn_id": turn_id},
            )
            self.store.add_edge(
                "supports",
                fact_node,
                answer_id,
                NODE_EDITED_KNOWLEDGE,
                NODE_ANSWER,
                payload={"reason": "curated fact included in answer context"},
            )

    def link_claim_evidence(self, claim_node: str, claim: Dict[str, Any], turn_log: Dict[str, Any]) -> None:
        evidence_sources = self.evidence_sources_from_turn(turn_log)
        verdicts = self.claim_verifier.verify(claim, evidence_sources)
        for verdict in verdicts:
            source_id = str(verdict.get("source_id", ""))
            if not source_id:
                continue
            source_type = str(verdict.get("source_type", ""))
            verdict_type = str(verdict.get("verdict", ""))
            if verdict_type == "supports":
                edge_type = "supports"
            elif verdict_type == "contradicts":
                edge_type = "contradicts"
            elif verdict_type == "partially_supports":
                edge_type = "supports"
            else:
                continue
            self.store.add_edge(
                edge_type,
                source_id,
                claim_node,
                source_type,
                NODE_CLAIM,
                confidence=verdict.get("confidence"),
                payload={"verifier": "HybridClaimVerifier", **verdict},
            )

    def evidence_sources_from_turn(self, turn_log: Dict[str, Any]) -> List[Dict[str, Any]]:
        sources: List[Dict[str, Any]] = []
        for detail in turn_log.get("retrieval", {}).get("retrieved_memory_details", []):
            memory_id = str(detail.get("memory_id", ""))
            content = str(detail.get("content", ""))
            if not memory_id:
                continue
            sources.append(
                {
                    "source_id": node_id_for_memory(memory_id),
                    "source_type": NODE_MEMORY,
                    "text": content,
                }
            )
            for source_id in detail.get("source_ids", []):
                if str(source_id).startswith("KB_"):
                    sources.append(
                        {
                            "source_id": node_id_for_kb(str(source_id)),
                            "source_type": NODE_KB_ITEM,
                            "text": content,
                        }
                    )
        for fact in turn_log.get("curated_knowledge", {}).get("curated_facts", []):
            fact_id = str(fact.get("fact_id", ""))
            if not fact_id:
                continue
            sources.append(
                {
                    "source_id": node_id_for_edited_knowledge(fact_id),
                    "source_type": NODE_EDITED_KNOWLEDGE,
                    "text": " ".join(
                        str(fact.get(key, ""))
                        for key in ("entity_name", "field", "value", "kb_id")
                    ),
                }
            )
        return dedupe_evidence_sources(sources)

    def import_curated_db(self) -> None:
        if not self.curated_db:
            return
        conn = sqlite3.connect(self.curated_db)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT * FROM curated_facts").fetchall():
            fact = decode_sqlite_row(row)
            fact_id = str(fact.get("fact_id"))
            fact_node = node_id_for_edited_knowledge(fact_id)
            self.store.upsert_node(
                fact_node,
                NODE_EDITED_KNOWLEDGE,
                f"{fact.get('kb_id')} {fact.get('field')}={fact.get('value')}",
                fact,
            )
            kb_id = str(fact.get("kb_id", ""))
            if kb_id:
                self.store.upsert_node(node_id_for_kb(kb_id), NODE_KB_ITEM, kb_id, {"kb_id": kb_id})
                self.store.add_edge(
                    "supports",
                    node_id_for_kb(kb_id),
                    fact_node,
                    NODE_KB_ITEM,
                    NODE_EDITED_KNOWLEDGE,
                    confidence=fact.get("confidence"),
                    payload={"reason": "curated fact grounded in base KB"},
                )
        for row in conn.execute("SELECT * FROM curated_fact_sources").fetchall():
            source = decode_sqlite_row(row)
            self.store.add_edge(
                "promoted_to",
                node_id_for_memory(str(source.get("source_memory_id"))),
                node_id_for_edited_knowledge(str(source.get("fact_id"))),
                NODE_MEMORY,
                NODE_EDITED_KNOWLEDGE,
                payload=source,
            )
        conn.close()

    def import_curation_report(self) -> None:
        if not self.curation_report:
            return
        data = load_json(self.curation_report)
        editor_id = node_id_for_agent("KnowledgeEditor")
        self.store.upsert_node(editor_id, NODE_EDITOR, "KnowledgeEditor", {"run_id": data.get("run_id")})
        for candidate in data.get("candidates", []):
            memory_id = str(candidate.get("memory_id", ""))
            for fact in candidate.get("facts", []):
                claim_id = str(fact.get("claim_id") or stable_id("curation_claim", memory_id, fact.get("claim_text", "")))
                claim_node = node_id_for_claim(claim_id)
                self.store.upsert_node(
                    claim_node,
                    NODE_CLAIM,
                    trim_label(str(fact.get("claim_text") or fact.get("value") or "")),
                    fact,
                )
                self.store.add_edge("extracts", node_id_for_memory(memory_id), claim_node, NODE_MEMORY, NODE_CLAIM)
                decision = str(fact.get("decision", ""))
                if decision == "approved":
                    fact_id = self.find_curated_fact_id(fact)
                    if fact_id:
                        self.store.add_edge(
                            "promoted_to",
                            claim_node,
                            node_id_for_edited_knowledge(fact_id),
                            NODE_CLAIM,
                            NODE_EDITED_KNOWLEDGE,
                            confidence=fact.get("confidence"),
                            payload={"run_id": data.get("run_id")},
                        )
                elif decision:
                    self.store.add_edge(
                        "rejected_by",
                        claim_node,
                        editor_id,
                        NODE_CLAIM,
                        NODE_EDITOR,
                        confidence=fact.get("confidence"),
                        payload={"decision": decision, "reason": fact.get("reason", "")},
                    )

    def find_curated_fact_id(self, fact: Dict[str, Any]) -> str:
        if not self.curated_db or not self.curated_db.exists():
            return ""
        conn = sqlite3.connect(self.curated_db)
        row = conn.execute(
            """
            SELECT fact_id FROM curated_facts
            WHERE kb_id = ? AND field = ? AND normalized_value = ?
            """,
            (fact.get("kb_id"), fact.get("field"), fact.get("normalized_value")),
        ).fetchone()
        conn.close()
        return str(row[0]) if row else ""

    def infer_contamination_and_repairs(self) -> None:
        rows = self.store.conn.execute(
            """
            SELECT node_id, payload
            FROM graph_nodes
            WHERE node_type = ?
            """,
            (NODE_MEMORY,),
        ).fetchall()
        for row in rows:
            memory_id = row["node_id"]
            payload = load_json_text(row["payload"], {})
            status = str(payload.get("contamination_status", ""))
            content = str(payload.get("content", ""))
            is_risky = status in {"suspected", "contaminated"} or contains_risky_claim(content)
            if not is_risky:
                continue

            used_targets = self.store.conn.execute(
                """
                SELECT source_id, source_type, target_id, target_type
                FROM graph_edges_unified
                WHERE edge_type = 'uses' AND target_id = ?
                """,
                (memory_id,),
            ).fetchall()
            for target in used_targets:
                agent_id = target["source_id"]
                if agent_id:
                    self.store.add_edge(
                        "contaminates",
                        memory_id,
                        agent_id,
                        NODE_MEMORY,
                        NODE_AGENT,
                        confidence=0.4,
                        payload={"rule": "risky_memory_used_by_agent"},
                    )

            supported_answers = self.store.conn.execute(
                """
                SELECT target_id
                FROM graph_edges_unified
                WHERE edge_type = 'supports'
                  AND source_id = ?
                  AND target_type = ?
                """,
                (memory_id, NODE_ANSWER),
            ).fetchall()
            for answer in supported_answers:
                self.store.add_edge(
                    "contaminates",
                    memory_id,
                    answer["target_id"],
                    NODE_MEMORY,
                    NODE_ANSWER,
                    confidence=0.55,
                    payload={"rule": "risky_memory_supports_answer"},
                )

            derived_children = self.store.conn.execute(
                """
                SELECT source_id
                FROM graph_edges_unified
                WHERE edge_type = 'derived_from' AND target_id = ?
                """,
                (memory_id,),
            ).fetchall()
            for child in derived_children:
                self.store.add_edge(
                    "contaminates",
                    memory_id,
                    child["source_id"],
                    NODE_MEMORY,
                    NODE_MEMORY,
                    confidence=0.6,
                    payload={"rule": "risky_memory_parent_of_derived_memory"},
                )

        self.infer_repairs_from_edited_knowledge()

    def infer_repairs_from_edited_knowledge(self) -> None:
        edited_rows = self.store.conn.execute(
            "SELECT node_id, payload FROM graph_nodes WHERE node_type = ?",
            (NODE_EDITED_KNOWLEDGE,),
        ).fetchall()
        memory_rows = self.store.conn.execute(
            "SELECT node_id, payload FROM graph_nodes WHERE node_type = ?",
            (NODE_MEMORY,),
        ).fetchall()
        for edited in edited_rows:
            fact = load_json_text(edited["payload"], {})
            kb_id = str(fact.get("kb_id", ""))
            value = str(fact.get("value", ""))
            if not kb_id or not value:
                continue
            for memory in memory_rows:
                payload = load_json_text(memory["payload"], {})
                content = str(payload.get("content", ""))
                source_ids = [str(x) for x in payload.get("source_ids", [])]
                if kb_id in source_ids and value not in content and contains_risky_claim(content):
                    self.store.add_edge(
                        "repairs",
                        edited["node_id"],
                        memory["node_id"],
                        NODE_EDITED_KNOWLEDGE,
                        NODE_MEMORY,
                        confidence=0.45,
                        payload={"rule": "edited_knowledge_same_kb_repairs_risky_memory"},
                    )
                    self.store.add_edge(
                        "deprecated_by",
                        memory["node_id"],
                        edited["node_id"],
                        NODE_MEMORY,
                        NODE_EDITED_KNOWLEDGE,
                        confidence=0.45,
                        payload={"rule": "risky_memory_deprecated_by_curated_fact"},
                    )

    def close(self) -> None:
        self.store.close()


def extract_claims(answer: str, turn_id: str) -> List[Dict[str, Any]]:
    text = strip_json_block(answer)
    parts = [
        part.strip(" 　-*#：:")
        for part in re.split(r"[。；\n]+", text)
        if len(part.strip()) >= 8
    ]
    claims = []
    for index, part in enumerate(parts[:12], start=1):
        claims.append(
            {
                "claim_id": stable_id("claim", turn_id, index, part),
                "turn_id": turn_id,
                "claim_index": index,
                "claim_text": part,
                "period_terms": extract_periods(part),
                "artifact_ids": extract_item_ids(part),
            }
        )
    return claims


def strip_json_block(text: str) -> str:
    return re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL).strip()


def weakly_supported(claim: str, evidence: str) -> bool:
    claim_terms = set(content_terms(claim))
    evidence_terms = set(content_terms(evidence))
    if not claim_terms or not evidence_terms:
        return False
    return len(claim_terms & evidence_terms) >= min(3, len(claim_terms))


def weakly_contradicted(claim: str, evidence: str) -> bool:
    claim_periods = set(extract_periods(claim))
    evidence_periods = set(extract_periods(evidence))
    return bool(claim_periods and evidence_periods and claim_periods.isdisjoint(evidence_periods))


def content_terms(text: str) -> List[str]:
    terms = re.findall(r"[\u4e00-\u9fff]{2,}|\d+(?:\.\d+)?", text)
    stop = {"根据", "知识库", "用户", "回答", "信息", "记载", "介绍", "可以", "不是", "没有"}
    return [term for term in terms if term not in stop]


PERIOD_TERMS = [
    "夏代晚期", "夏代早期", "夏代", "商代早期", "商代中期", "商代晚期", "商代",
    "西周早期", "西周中期", "西周晚期", "西周", "春秋早期", "春秋中期", "春秋晚期",
    "春秋时期", "春秋", "战国早期", "战国中期", "战国晚期", "战国时期", "战国",
    "秦代", "西汉", "东汉", "汉代", "唐代", "宋代", "元代", "明代", "清代",
]


def extract_periods(text: str) -> List[str]:
    return [term for term in PERIOD_TERMS if term in text]


def extract_item_ids(text: str) -> List[str]:
    ids = []
    for match in re.finditer(r"(?:ID|KB_)\s*[:：]?\s*(\d{5,})", text):
        if match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def contains_risky_claim(text: str) -> bool:
    risky_terms = [
        "错误", "不符", "冲突", "矛盾", "污染", "无依据", "未记载", "请记住",
        "暂时按", "以这个为准", "写成一条后续可用的记忆", "反复确认",
        "纠正", "修正", "废弃", "弃用",
    ]
    return any(term in text for term in risky_terms)


def memory_label(memory: Dict[str, Any]) -> str:
    source_ids = memory.get("source_ids", [])
    if source_ids:
        return f"{memory.get('memory_id')} {'/'.join(str(x) for x in source_ids[:2])}"
    return f"{memory.get('memory_id')} {trim_label(str(memory.get('content', '')))}"


def normalize_node_id(source_type: str, source_id: str) -> str:
    normalized = normalize_node_type(source_type)
    if normalized == NODE_MEMORY:
        return node_id_for_memory(source_id)
    if normalized == NODE_KB_ITEM:
        return node_id_for_kb(source_id)
    if normalized == NODE_AGENT:
        return node_id_for_agent(source_id)
    if normalized == NODE_ANSWER:
        return node_id_for_answer(source_id)
    if normalized == NODE_CLAIM:
        return node_id_for_claim(source_id)
    return f"{normalized}:{source_id}"


def normalize_node_type(source_type: str) -> str:
    lower = source_type.lower()
    if lower in {"memory", "memories"}:
        return NODE_MEMORY
    if lower in {"knowledge_base", "kb", "kbitem"}:
        return NODE_KB_ITEM
    if lower in {"agent", "answer_agent"}:
        return NODE_AGENT
    if lower == "answer":
        return NODE_ANSWER
    if lower == "claim":
        return NODE_CLAIM
    return source_type or "Unknown"


def node_id_for_turn(turn_id: str) -> str:
    return f"turn:{turn_id}"


def node_id_for_question(turn_id: str) -> str:
    return f"question:{turn_id}"


def node_id_for_answer(turn_id: str) -> str:
    return f"answer:{turn_id}"


def node_id_for_memory(memory_id: str) -> str:
    return f"memory:{memory_id}"


def node_id_for_kb(kb_id: str) -> str:
    return f"kb:{kb_id}"


def node_id_for_edited_knowledge(fact_id: str) -> str:
    return f"edited:{fact_id}"


def node_id_for_claim(claim_id: str) -> str:
    return f"claim:{claim_id}"


def node_id_for_agent(agent_id: str) -> str:
    return f"agent:{agent_id}"


def decode_sqlite_row(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    for key in ("source_ids", "derived_from", "metadata", "retrieved_memory_ids", "distances", "used_memory_ids", "reasons"):
        if key in data:
            data[key] = load_json_text(data[key], [] if key != "metadata" else {})
    return data


def dedupe_evidence_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for source in sources:
        key = (source.get("source_id"), source.get("source_type"), source.get("text"))
        if key in seen:
            continue
        seen.add(key)
        result.append(source)
    return result


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def load_json_text(value: Any, default: Any) -> Any:
    if not isinstance(value, str):
        return value if value is not None else default
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def stable_id(prefix: str, *parts: Any) -> str:
    text = "\u241f".join(str(part) for part in parts)
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def trim_label(text: str, length: int = 80) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= length:
        return clean
    return clean[: length - 3] + "..."


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
