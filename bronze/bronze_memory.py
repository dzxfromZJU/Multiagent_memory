import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArchitectureMemory:
    """Per-architecture conversation and edited-knowledge memory."""

    def __init__(self, memory_file: str, vector_db: Optional[object] = None) -> None:
        self.memory_file = Path(memory_file)
        self.vector_db = vector_db
        self.memory = self.load_memory()
        if not self.memory_file.exists():
            self.save_memory()

    def load_memory(self) -> Dict[str, Any]:
        if not self.memory_file.exists() or self.memory_file.stat().st_size == 0:
            return {"conversations": [], "knowledge_edits": {}}

        try:
            with self.memory_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            backup_path = self.memory_file.with_suffix(
                self.memory_file.suffix + f".broken-{int(time.time())}"
            )
            self.memory_file.replace(backup_path)
            return {"conversations": [], "knowledge_edits": {}}

        if not isinstance(data, dict):
            return {"conversations": [], "knowledge_edits": {}}
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
    ) -> None:
        record = {
            "timestamp": time.time(),
            "architecture": architecture,
            "user_question": user_question,
            "final_answer": final_answer,
            "validation": validation,
            "supporting_context": supporting_context or [],
        }
        self.memory["conversations"].append(record)
        self.save_memory()

        if self.vector_db and final_answer:
            self.vector_db.add_text(
                f"历史对话({architecture})\n用户问题: {user_question}\n系统回答: {final_answer}"
            )

    def add_knowledge_edit(self, key: str, value: Any, *, source: str = "manual") -> None:
        self.memory["knowledge_edits"][key] = {
            "value": value,
            "source": source,
            "timestamp": time.time(),
        }
        self.save_memory()

        if self.vector_db:
            self.vector_db.add_text(f"知识编辑: {key}\n内容: {value}\n来源: {source}")

    def get_recent_conversations(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.memory["conversations"][-limit:]

    def get_relevant_memory(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if self.vector_db:
            return self.vector_db.search(query, top_k=top_k)

        matched = []
        for item in self.memory["conversations"]:
            if query in item.get("user_question", "") or query in item.get("final_answer", ""):
                matched.append(item)
        return matched[-top_k:]
