#!/usr/bin/env python3
"""FAISS-backed memory manager with SQLite provenance metadata.

FAISS stores embeddings for nearest-neighbor retrieval. SQLite stores memory
metadata, retrieval/usage logs, verifier records, and provenance graph edges.
The class keeps the old VectorDatabase name so existing experiment scripts can
continue to call add_text(), search(), save(), and clear().
"""

from __future__ import annotations

import json
import os
import pickle
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


SOURCE_TYPES = {
    "knowledge_base",
    "user_input",
    "agent_inference",
    "memory_derived",
    "external_search",
    "unknown",
}

GRAPH_EDGE_TYPES = {
    "retrieved",
    "cited",
    "supports",
    "derived_from",
    "written_by",
    "contradicted_by",
    "contaminates",
}


class VectorDatabase:
    """Memory Manager facade over FAISS + SQLite provenance storage."""

    def __init__(
        self,
        db_path: str = "vector_db",
        model_name: str = "all-MiniLM-L6-v2",
        model_path: Optional[str] = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        if model_path and Path(model_path).exists():
            print(f"Loading embedding model from local path: {model_path}")
            self.model = SentenceTransformer(model_path)
        else:
            print(f"Loading embedding model from Hugging Face: {model_name}")
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            os.environ["TRANSFORMERS_DOWNLOAD_TIMEOUT"] = "300"
            self.model = SentenceTransformer(model_name)

        self.index: Optional[faiss.Index] = None
        self.id_to_text: Dict[int, str] = {}
        self.vector_to_memory_id: Dict[int, str] = {}
        self.next_id = 0
        self.sqlite_path = self.db_path / "metadata.sqlite3"
        self.conn = sqlite3.connect(self.sqlite_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        self.load()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                vector_id INTEGER UNIQUE,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_ids TEXT NOT NULL DEFAULT '[]',
                created_by TEXT NOT NULL DEFAULT 'unknown',
                created_turn TEXT,
                confidence REAL NOT NULL DEFAULT 0.5,
                contamination_status TEXT NOT NULL DEFAULT 'clean',
                derived_from TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS retrieval_log (
                retrieval_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                agent_id TEXT NOT NULL DEFAULT 'unknown',
                turn_id TEXT,
                retrieved_memory_ids TEXT NOT NULL,
                distances TEXT NOT NULL,
                top_k INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usage_log (
                usage_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                turn_id TEXT,
                answer_id TEXT,
                claim_id TEXT,
                used_memory_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                edge_id TEXT PRIMARY KEY,
                edge_type TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                agent_id TEXT,
                turn_id TEXT,
                confidence REAL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS verifier_log (
                verification_id TEXT PRIMARY KEY,
                new_memory_id TEXT NOT NULL,
                derived_from TEXT NOT NULL,
                verifier_agent TEXT NOT NULL,
                verdict TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasons TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memories_vector_id ON memories(vector_id);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_type, source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_type, target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON graph_edges(edge_type);
            """
        )
        self.conn.commit()

    def load(self) -> None:
        index_path = self.db_path / "index.faiss"
        id_map_path = self.db_path / "id_to_text.pkl"

        if index_path.exists() and id_map_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                with id_map_path.open("rb") as file:
                    data = pickle.load(file)
                self.id_to_text = dict(data.get("id_to_text", {}))
                self.next_id = int(data.get("next_id", len(self.id_to_text)))
                self.vector_to_memory_id = dict(data.get("vector_to_memory_id", {}))
                self._migrate_legacy_vectors()
                print(f"Loaded vector database with {len(self.id_to_text)} records.")
                return
            except Exception as exc:
                print(f"Failed to load vector database, rebuilding empty index: {exc}")

        self.initialize_index()

    def initialize_index(self) -> None:
        sample_embedding = self.model.encode(["sample"])[0]
        self.index = faiss.IndexFlatL2(len(sample_embedding))
        self.id_to_text = {}
        self.vector_to_memory_id = {}
        self.next_id = 0
        print(f"Initialized vector index, dimension={len(sample_embedding)}")

    def _migrate_legacy_vectors(self) -> None:
        """Create SQLite rows for vectors produced before metadata existed."""
        changed = False
        for vector_id, text in self.id_to_text.items():
            if vector_id in self.vector_to_memory_id:
                continue
            memory_id = self._new_memory_id()
            now = self.now_iso()
            self.conn.execute(
                """
                INSERT OR IGNORE INTO memories (
                    memory_id, vector_id, content, source_type, source_ids,
                    created_by, created_turn, confidence, contamination_status,
                    derived_from, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    int(vector_id),
                    str(text),
                    "unknown",
                    "[]",
                    "legacy_vector_db",
                    None,
                    0.5,
                    "unknown",
                    "[]",
                    json.dumps({"migrated_from": "id_to_text.pkl"}, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            self.vector_to_memory_id[int(vector_id)] = memory_id
            changed = True
        if changed:
            self.conn.commit()
            self.save()

    def save(self) -> None:
        if self.index is None:
            return
        faiss.write_index(self.index, str(self.db_path / "index.faiss"))
        with (self.db_path / "id_to_text.pkl").open("wb") as file:
            pickle.dump(
                {
                    "id_to_text": self.id_to_text,
                    "next_id": self.next_id,
                    "vector_to_memory_id": self.vector_to_memory_id,
                },
                file,
            )
        self.conn.commit()
        print(f"Saved vector database with {len(self.id_to_text)} records.")

    def add_text(
        self,
        text: str,
        *,
        source_type: str = "unknown",
        source_ids: Optional[Sequence[str]] = None,
        created_by: str = "unknown",
        created_turn: Optional[str] = None,
        confidence: float = 0.5,
        contamination_status: str = "clean",
        derived_from: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.add_memory(
            content=text,
            source_type=source_type,
            source_ids=source_ids,
            created_by=created_by,
            created_turn=created_turn,
            confidence=confidence,
            contamination_status=contamination_status,
            derived_from=derived_from,
            metadata=metadata,
        )

    def add_memory(
        self,
        *,
        content: str,
        source_type: str = "unknown",
        source_ids: Optional[Sequence[str]] = None,
        created_by: str = "unknown",
        created_turn: Optional[str] = None,
        confidence: float = 0.5,
        contamination_status: str = "clean",
        derived_from: Optional[Sequence[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if self.index is None:
            self.initialize_index()
        assert self.index is not None

        source_type = source_type if source_type in SOURCE_TYPES else "unknown"
        source_ids = list(source_ids or [])
        derived_from = list(derived_from or [])
        memory_id = self._new_memory_id()
        vector_id = self.next_id
        embedding = self.model.encode([content])[0]
        self.index.add(np.array([embedding], dtype=np.float32))

        self.id_to_text[vector_id] = content
        self.vector_to_memory_id[vector_id] = memory_id
        self.next_id += 1

        now = self.now_iso()
        self.conn.execute(
            """
            INSERT INTO memories (
                memory_id, vector_id, content, source_type, source_ids,
                created_by, created_turn, confidence, contamination_status,
                derived_from, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                vector_id,
                content,
                source_type,
                self._json(source_ids),
                created_by,
                created_turn,
                float(confidence),
                contamination_status,
                self._json(derived_from),
                self._json(metadata or {}),
                now,
                now,
            ),
        )
        self.record_graph_edge(
            "written_by",
            source_type="agent",
            source_id=created_by,
            target_type="memory",
            target_id=memory_id,
            turn_id=created_turn,
            confidence=confidence,
        )
        for parent_id in derived_from:
            self.record_graph_edge(
                "derived_from",
                source_type="memory",
                source_id=memory_id,
                target_type="memory",
                target_id=parent_id,
                agent_id=created_by,
                turn_id=created_turn,
                confidence=confidence,
            )
        if contamination_status == "contaminated":
            for parent_id in derived_from:
                self.record_graph_edge(
                    "contaminates",
                    source_type="memory",
                    source_id=parent_id,
                    target_type="memory",
                    target_id=memory_id,
                    agent_id=created_by,
                    turn_id=created_turn,
                    confidence=confidence,
                )
        self.conn.commit()

        if self.next_id % 10 == 0:
            self.save()
        return memory_id

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        agent_id: str = "unknown",
        turn_id: Optional[str] = None,
        log_retrieval: bool = True,
    ) -> List[Dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []

        exact_results = self._exact_id_search(query)
        query_embedding = self.model.encode([query])[0]
        distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), top_k)
        results: List[Dict[str, Any]] = list(exact_results)
        seen_memory_ids = {str(item.get("memory_id")) for item in results if item.get("memory_id")}

        for rank, idx in enumerate(indices[0], start=1):
            if idx == -1:
                continue
            vector_id = int(idx)
            memory_id = self.vector_to_memory_id.get(vector_id)
            if memory_id and memory_id in seen_memory_ids:
                continue
            memory = self.get_memory(memory_id) if memory_id else None
            text = memory["content"] if memory else self.id_to_text.get(vector_id, "")
            if not text:
                continue
            seen_memory_ids.add(str(memory_id))
            results.append(
                {
                    "rank": len(results) + 1,
                    "memory_id": memory_id,
                    "vector_id": vector_id,
                    "text": text,
                    "distance": float(distances[0][rank - 1]),
                    "metadata": memory or {},
                }
            )
            if len(results) >= top_k:
                break

        if log_retrieval and results:
            self.log_retrieval(query, results, agent_id=agent_id, turn_id=turn_id, top_k=top_k)
        return results

    def _exact_id_search(self, query: str) -> List[Dict[str, Any]]:
        kb_ids = set(re.findall(r"\bKB_\d+\b", query))
        for raw_id in re.findall(r"(?:ID|id|编号)\s*[:：]?\s*(\d{5,})", query):
            kb_ids.add(f"KB_{raw_id}")
        if not kb_ids:
            return []

        results: List[Dict[str, Any]] = []
        for kb_id in sorted(kb_ids):
            rows = self.conn.execute(
                """
                SELECT memory_id
                FROM memories
                WHERE source_type = 'knowledge_base'
                  AND source_ids LIKE ?
                ORDER BY created_at ASC
                """,
                (f"%{kb_id}%",),
            ).fetchall()
            for row in rows:
                memory = self.get_memory(str(row["memory_id"]))
                if not memory:
                    continue
                results.append(
                    {
                        "rank": len(results) + 1,
                        "memory_id": memory["memory_id"],
                        "vector_id": memory["vector_id"],
                        "text": memory["content"],
                        "distance": 0.0,
                        "metadata": memory,
                        "retrieval_type": "exact_id",
                    }
                )
        return results

    def log_retrieval(
        self,
        query: str,
        results: Sequence[Dict[str, Any]],
        *,
        agent_id: str,
        turn_id: Optional[str],
        top_k: int,
    ) -> str:
        retrieval_id = f"ret_{uuid.uuid4().hex[:12]}"
        memory_ids = [str(item["memory_id"]) for item in results if item.get("memory_id")]
        distances = {
            str(item["memory_id"]): item.get("distance")
            for item in results
            if item.get("memory_id")
        }
        self.conn.execute(
            """
            INSERT INTO retrieval_log (
                retrieval_id, query, agent_id, turn_id, retrieved_memory_ids,
                distances, top_k, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                retrieval_id,
                query,
                agent_id,
                turn_id,
                self._json(memory_ids),
                self._json(distances),
                top_k,
                self.now_iso(),
            ),
        )
        for memory_id in memory_ids:
            self.record_graph_edge(
                "retrieved",
                source_type="agent",
                source_id=agent_id,
                target_type="memory",
                target_id=memory_id,
                turn_id=turn_id,
                metadata={"retrieval_id": retrieval_id, "query": query},
            )
        self.conn.commit()
        return retrieval_id

    def log_usage(
        self,
        *,
        agent_id: str,
        used_memory_ids: Sequence[str],
        turn_id: Optional[str] = None,
        answer_id: Optional[str] = None,
        claim_id: Optional[str] = None,
    ) -> str:
        usage_id = f"use_{uuid.uuid4().hex[:12]}"
        used_memory_ids = [str(item) for item in used_memory_ids if item]
        self.conn.execute(
            """
            INSERT INTO usage_log (
                usage_id, agent_id, turn_id, answer_id, claim_id,
                used_memory_ids, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usage_id,
                agent_id,
                turn_id,
                answer_id,
                claim_id,
                self._json(used_memory_ids),
                self.now_iso(),
            ),
        )
        for memory_id in used_memory_ids:
            self.record_graph_edge(
                "cited",
                source_type="agent",
                source_id=agent_id,
                target_type="memory",
                target_id=memory_id,
                turn_id=turn_id,
                metadata={"usage_id": usage_id, "answer_id": answer_id, "claim_id": claim_id},
            )
            if claim_id:
                self.record_graph_edge(
                    "supports",
                    source_type="memory",
                    source_id=memory_id,
                    target_type="claim",
                    target_id=claim_id,
                    agent_id=agent_id,
                    turn_id=turn_id,
                    metadata={"usage_id": usage_id},
                )
        self.conn.commit()
        return usage_id

    def verify_derived_from(
        self,
        *,
        new_memory_id: str,
        derived_from: Sequence[str],
        verifier_agent: str = "Verifier",
        min_overlap: float = 0.08,
    ) -> Dict[str, Any]:
        """Lightweight verifier for whether parent memories support a new memory.

        This is intentionally deterministic. A stronger LLM verifier can call
        this method with its verdict later, but this provides an executable
        baseline for experiments and graph logging.
        """
        new_memory = self.get_memory(new_memory_id)
        parents = [self.get_memory(item) for item in derived_from]
        parents = [item for item in parents if item]
        reasons: List[str] = []

        if not new_memory:
            verdict = "unsupported"
            confidence = 0.0
            reasons.append("new memory does not exist")
        elif not parents:
            verdict = "unsupported"
            confidence = 0.1
            reasons.append("no derived_from parent memories exist")
        else:
            parent_text = " ".join(str(item["content"]) for item in parents)
            overlap = self._token_overlap(str(new_memory["content"]), parent_text)
            confidence = min(0.95, 0.35 + overlap)
            if overlap >= min_overlap:
                verdict = "supported"
                reasons.append(f"lexical overlap with parent memories is {overlap:.3f}")
            else:
                verdict = "unsupported"
                reasons.append(f"lexical overlap with parent memories is only {overlap:.3f}")

        verification_id = f"ver_{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            """
            INSERT INTO verifier_log (
                verification_id, new_memory_id, derived_from, verifier_agent,
                verdict, confidence, reasons, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                verification_id,
                new_memory_id,
                self._json(list(derived_from)),
                verifier_agent,
                verdict,
                float(confidence),
                self._json(reasons),
                self.now_iso(),
            ),
        )
        if verdict == "unsupported":
            for parent_id in derived_from:
                self.record_graph_edge(
                    "contradicted_by",
                    source_type="memory",
                    source_id=new_memory_id,
                    target_type="memory",
                    target_id=str(parent_id),
                    agent_id=verifier_agent,
                    confidence=confidence,
                    metadata={"verification_id": verification_id, "reasons": reasons},
                )
        self.conn.commit()
        return {
            "verification_id": verification_id,
            "new_memory_id": new_memory_id,
            "derived_from": list(derived_from),
            "verdict": verdict,
            "confidence": confidence,
            "reasons": reasons,
        }

    def mark_contaminated(
        self,
        memory_id: str,
        *,
        reason: str,
        source_memory_id: Optional[str] = None,
        confidence: float = 1.0,
    ) -> None:
        self.conn.execute(
            """
            UPDATE memories
            SET contamination_status = 'contaminated', updated_at = ?
            WHERE memory_id = ?
            """,
            (self.now_iso(), memory_id),
        )
        if source_memory_id:
            self.record_graph_edge(
                "contaminates",
                source_type="memory",
                source_id=source_memory_id,
                target_type="memory",
                target_id=memory_id,
                confidence=confidence,
                metadata={"reason": reason},
            )
        self.conn.commit()

    def trace_contamination_paths(
        self,
        start_memory_id: Optional[str] = None,
        *,
        max_depth: int = 5,
    ) -> List[List[Dict[str, Any]]]:
        starts = [start_memory_id] if start_memory_id else self._contaminated_memory_ids()
        paths: List[List[Dict[str, Any]]] = []
        for memory_id in starts:
            if memory_id:
                self._trace_from(memory_id, [], paths, max_depth)
        return paths

    def _trace_from(
        self,
        memory_id: str,
        prefix: List[Dict[str, Any]],
        paths: List[List[Dict[str, Any]]],
        depth_left: int,
    ) -> None:
        if depth_left <= 0:
            return
        outgoing_rows = self.conn.execute(
            """
            SELECT * FROM graph_edges
            WHERE source_type = 'memory'
              AND source_id = ?
              AND edge_type IN ('contaminates', 'supports')
            ORDER BY created_at ASC
            """,
            (memory_id,),
        ).fetchall()
        derived_child_rows = self.conn.execute(
            """
            SELECT * FROM graph_edges
            WHERE target_type = 'memory'
              AND target_id = ?
              AND edge_type = 'derived_from'
            ORDER BY created_at ASC
            """,
            (memory_id,),
        ).fetchall()
        for row in list(outgoing_rows) + list(derived_child_rows):
            edge = dict(row)
            next_path = prefix + [edge]
            paths.append(next_path)
            next_memory_id = None
            if edge["edge_type"] == "derived_from":
                next_memory_id = edge["source_id"]
            elif edge["target_type"] == "memory":
                next_memory_id = edge["target_id"]
            if next_memory_id and next_memory_id != memory_id:
                self._trace_from(next_memory_id, next_path, paths, depth_left - 1)

    def record_graph_edge(
        self,
        edge_type: str,
        *,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        agent_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if edge_type not in GRAPH_EDGE_TYPES:
            raise ValueError(f"Unsupported graph edge type: {edge_type}")
        edge_id = f"edge_{uuid.uuid4().hex[:12]}"
        self.conn.execute(
            """
            INSERT INTO graph_edges (
                edge_id, edge_type, source_type, source_id, target_type,
                target_id, agent_id, turn_id, confidence, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge_id,
                edge_type,
                source_type,
                source_id,
                target_type,
                target_id,
                agent_id,
                turn_id,
                confidence,
                self._json(metadata or {}),
                self.now_iso(),
            ),
        )
        return edge_id

    def get_memory(self, memory_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not memory_id:
            return None
        row = self.conn.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        for key in ("source_ids", "derived_from", "metadata"):
            item[key] = self._loads(item.get(key), [] if key != "metadata" else {})
        return item

    def list_graph_edges(self, edge_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if edge_type:
            rows = self.conn.execute(
                "SELECT * FROM graph_edges WHERE edge_type = ? ORDER BY created_at ASC",
                (edge_type,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM graph_edges ORDER BY created_at ASC").fetchall()
        return [dict(row) for row in rows]

    def add_knowledge_base(self, knowledge_base: Dict[str, Dict[str, Any]]) -> None:
        for artifact_name, artifact_info in knowledge_base.items():
            text = (
                f"{artifact_name}: {artifact_info.get('描述', '')} "
                f"年代: {artifact_info.get('年代', '')} "
                f"出土地点: {artifact_info.get('出土地点', '')}"
            )
            self.add_text(
                text,
                source_type="knowledge_base",
                source_ids=[str(artifact_name)],
                created_by="knowledge_base_loader",
                confidence=1.0,
                contamination_status="clean",
            )
        self.save()

    def clear(self) -> None:
        self.initialize_index()
        self.conn.executescript(
            """
            DELETE FROM verifier_log;
            DELETE FROM usage_log;
            DELETE FROM retrieval_log;
            DELETE FROM graph_edges;
            DELETE FROM memories;
            """
        )
        self.conn.commit()
        self.save()

    def close(self) -> None:
        self.save()
        self.conn.close()

    def _contaminated_memory_ids(self) -> List[str]:
        rows = self.conn.execute(
            "SELECT memory_id FROM memories WHERE contamination_status = 'contaminated'"
        ).fetchall()
        return [str(row["memory_id"]) for row in rows]

    def _new_memory_id(self) -> str:
        return f"mem_{uuid.uuid4().hex[:12]}"

    def _json(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _loads(self, value: Any, default: Any) -> Any:
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return default

    def _token_overlap(self, left: str, right: str) -> float:
        left_tokens = self._tokens(left)
        right_tokens = self._tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / max(1, len(left_tokens))

    def _tokens(self, text: str) -> set[str]:
        # Works tolerably for mixed Chinese/ASCII experiment text without adding deps.
        chunks = [text[i : i + 2] for i in range(max(0, len(text) - 1))]
        words = [part.lower() for part in text.replace("\n", " ").split() if part.strip()]
        return set(chunks + words)

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


MemoryManager = VectorDatabase
