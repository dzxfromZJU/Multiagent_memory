import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArchitectureMemory:
    """Three-layer per-architecture memory store."""

    def __init__(self, memory_file: str, vector_db: Optional[object] = None) -> None:
        self.memory_file = Path(memory_file)
        self.vector_db = vector_db
        self.memory = self.load_memory()
        if not self.memory_file.exists():
            self.save_memory()

    def empty_memory(self) -> Dict[str, Any]:
        return {
            "raw_dialogue_log": [],
            "memory_candidates": [],
            "committed_memories": [],
            "conversations": [],
            "knowledge_edits": {},
        }

    def load_memory(self) -> Dict[str, Any]:
        if not self.memory_file.exists() or self.memory_file.stat().st_size == 0:
            return self.empty_memory()

        try:
            with self.memory_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            backup_path = self.memory_file.with_suffix(
                self.memory_file.suffix + f".broken-{int(time.time())}"
            )
            self.memory_file.replace(backup_path)
            return self.empty_memory()

        if not isinstance(data, dict):
            return self.empty_memory()

        data.setdefault("raw_dialogue_log", [])
        data.setdefault("memory_candidates", [])
        data.setdefault("committed_memories", [])
        data.setdefault("conversations", [])
        data.setdefault("knowledge_edits", {})
        return data

    def save_memory(self) -> None:
        with self.memory_file.open("w", encoding="utf-8") as file:
            json.dump(self.memory, file, ensure_ascii=False, indent=2)

    def add_conversation(
        self,
        user_question: str,
        final_answer: str,
        *,
        architecture: str,
        validation: str = "",
        supporting_context: Optional[List[str]] = None,
        raw_history: Optional[List[Dict[str, Any]]] = None,
        committed_memory_type: str = "final_answer",
        retrieved_memory_ids: Optional[List[str]] = None,
        used_memory_ids: Optional[List[str]] = None,
        derived_from: Optional[List[str]] = None,
    ) -> None:
        conversation_id = self.next_id("conv", self.memory["conversations"], "conversation_id")
        timestamp = self.now_iso()
        raw_entries = self.build_raw_dialogue_log(conversation_id, raw_history or [])
        candidate_entries = self.build_memory_candidates(conversation_id, raw_entries)
        source_candidates = [item["candidate_id"] for item in candidate_entries]

        committed_memory_id = ""
        if final_answer:
            committed_memory_id = self.next_id(
                "mem", self.memory["committed_memories"], "memory_id"
            )
            self.memory["committed_memories"].append(
                {
                    "memory_id": committed_memory_id,
                    "conversation_id": conversation_id,
                    "content": final_answer,
                    "memory_type": committed_memory_type,
                    "status": "active",
                    "source_candidates": source_candidates,
                    "corrects": [],
                    "timestamp": timestamp,
                    "architecture": architecture,
                    "supporting_context": supporting_context or [],
                    "validation": validation,
                    "retrieved_memory_ids": retrieved_memory_ids or [],
                    "used_memory_ids": used_memory_ids or [],
                    "derived_from": derived_from or [],
                }
            )

        record = {
            "conversation_id": conversation_id,
            "timestamp": timestamp,
            "architecture": architecture,
            "user_question": user_question,
            "final_answer": final_answer,
            "validation": validation,
            "supporting_context": supporting_context or [],
            "retrieved_memory_ids": retrieved_memory_ids or [],
            "used_memory_ids": used_memory_ids or [],
            "derived_from": derived_from or [],
            "raw_log_ids": [item["log_id"] for item in raw_entries],
            "candidate_ids": source_candidates,
            "committed_memory_id": committed_memory_id,
        }
        self.memory["raw_dialogue_log"].extend(raw_entries)
        self.memory["memory_candidates"].extend(candidate_entries)
        self.memory["conversations"].append(record)
        self.save_memory()

        if self.vector_db and final_answer:
            self.vector_db.add_text(
                f"Committed memory ({architecture})\n"
                f"Conversation: {conversation_id}\n"
                f"Memory type: {committed_memory_type}\n"
                f"User question: {user_question}\n"
                f"Content: {final_answer}",
                source_type="memory_derived" if derived_from else "agent_inference",
                source_ids=used_memory_ids or [],
                created_by="ArchitectureMemory",
                created_turn=conversation_id,
                confidence=0.6,
                contamination_status="clean",
                derived_from=derived_from or [],
                metadata={
                    "architecture": architecture,
                    "committed_memory_id": committed_memory_id,
                    "retrieved_memory_ids": retrieved_memory_ids or [],
                },
            )
            self.vector_db.save()

    def add_knowledge_edit(self, key: str, value: Any, *, source: str = "manual") -> None:
        memory_id = self.next_id("mem", self.memory["committed_memories"], "memory_id")
        timestamp = self.now_iso()
        content = f"{key}: {value}"
        self.memory["knowledge_edits"][key] = {
            "value": value,
            "source": source,
            "timestamp": timestamp,
            "committed_memory_id": memory_id,
        }
        self.memory["committed_memories"].append(
            {
                "memory_id": memory_id,
                "conversation_id": None,
                "content": content,
                "memory_type": "knowledge_edit",
                "status": "active",
                "source_candidates": [],
                "corrects": [],
                "timestamp": timestamp,
                "source": source,
            }
        )
        self.save_memory()

        if self.vector_db:
            self.vector_db.add_text(f"Committed knowledge edit\nContent: {content}\nSource: {source}")
            self.vector_db.save()

    def commit_memory(
        self,
        content: str,
        *,
        memory_type: str,
        source_candidates: Optional[List[str]] = None,
        corrects: Optional[List[str]] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        add_to_vector: bool = True,
    ) -> str:
        memory_id = self.next_id("mem", self.memory["committed_memories"], "memory_id")
        record = {
            "memory_id": memory_id,
            "conversation_id": conversation_id,
            "content": content,
            "memory_type": memory_type,
            "status": "active",
            "source_candidates": source_candidates or [],
            "corrects": corrects or [],
            "timestamp": self.now_iso(),
        }
        if metadata:
            record["metadata"] = metadata
        self.memory["committed_memories"].append(record)
        self.save_memory()

        if self.vector_db and add_to_vector:
            self.vector_db.add_text(
                f"Committed memory\n"
                f"Memory ID: {memory_id}\n"
                f"Memory type: {memory_type}\n"
                f"Content: {content}"
            )
            self.vector_db.save()
        return memory_id

    def deactivate_committed_memory(self, memory_id: str, *, reason: str) -> bool:
        for item in self.memory["committed_memories"]:
            if item.get("memory_id") != memory_id:
                continue
            item["status"] = "inactive"
            item["deactivated_at"] = self.now_iso()
            item["deactivation_reason"] = reason
            self.save_memory()
            return True
        return False

    def get_active_committed_memories(self) -> List[Dict[str, Any]]:
        return [
            item
            for item in self.memory["committed_memories"]
            if item.get("status") == "active"
        ]

    def get_recent_conversations(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.memory["conversations"][-limit:]

    def get_relevant_memory(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if self.vector_db:
            return self.vector_db.search(query, top_k=top_k)

        matched = []
        for item in self.memory["committed_memories"]:
            if item.get("status") == "active" and query in item.get("content", ""):
                matched.append(item)
        return matched[-top_k:]

    def build_raw_dialogue_log(
        self,
        conversation_id: str,
        raw_history: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        entries = []
        for turn_id, message in enumerate(raw_history, start=1):
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            agent = str(message.get("name") or message.get("role") or "unknown")
            role = str(message.get("role") or self.infer_role(agent))
            entries.append(
                {
                    "log_id": self.next_id(
                        "log",
                        self.memory["raw_dialogue_log"] + entries,
                        "log_id",
                    ),
                    "conversation_id": conversation_id,
                    "turn_id": turn_id,
                    "agent": agent,
                    "role": role,
                    "content": content,
                    "timestamp": self.now_iso(),
                }
            )
        return entries

    def build_memory_candidates(
        self,
        conversation_id: str,
        raw_entries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        candidates = []
        for entry in raw_entries:
            if entry["role"] == "user" or entry["agent"] == "User":
                continue
            candidates.append(
                {
                    "candidate_id": self.next_id(
                        "cand",
                        self.memory["memory_candidates"] + candidates,
                        "candidate_id",
                    ),
                    "conversation_id": conversation_id,
                    "agent": entry["agent"],
                    "content": entry["content"],
                    "memory_type": self.candidate_type(entry["agent"]),
                    "status": "pending",
                    "confidence": self.default_confidence(entry["agent"]),
                    "turn_id": entry["turn_id"],
                    "source_log_id": entry["log_id"],
                    "timestamp": self.now_iso(),
                }
            )
        return candidates

    def next_id(self, prefix: str, collection: List[Dict[str, Any]], field: str) -> str:
        max_number = 0
        marker = f"{prefix}_"
        for item in collection:
            value = str(item.get(field, ""))
            if not value.startswith(marker):
                continue
            try:
                max_number = max(max_number, int(value.removeprefix(marker)))
            except ValueError:
                continue
        return f"{prefix}_{max_number + 1:06d}"

    def infer_role(self, agent: str) -> str:
        return "user" if agent == "User" else "assistant"

    def candidate_type(self, agent: str) -> str:
        if agent in {"Validator", "EvidencePeer"}:
            return "validation"
        if agent == "Analyzer":
            return "analysis"
        return "claim"

    def default_confidence(self, agent: str) -> float:
        if agent in {"Validator", "EvidencePeer"}:
            return 0.7
        if agent == "Analyzer":
            return 0.5
        return 0.6

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
