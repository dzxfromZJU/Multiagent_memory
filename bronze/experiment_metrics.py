import json
from pathlib import Path
from typing import Any, Dict, List

from bronze.memory_auditor import AuditResult, MemoryAuditor


class MemoryExperimentAnalyzer:
    """Build experiment evidence for memory pollution and edit effectiveness."""

    def __init__(self, auditor: MemoryAuditor) -> None:
        self.auditor = auditor
        self.memory = auditor.memory

    def build_report(self) -> Dict[str, Any]:
        audit_results = [
            self.auditor.audit_memory(item)
            for item in self.memory.memory.get("committed_memories", [])
            if item.get("status") == "active"
        ]
        audit_by_id = {item.memory_id: item for item in audit_results}
        pollution_chains = self.find_pollution_chains(audit_by_id)
        correction_pairs = self.find_correction_pairs()

        return {
            "memory_counts": self.memory_counts(),
            "audit_summary": self.audit_summary(audit_results),
            "pollution_chains": pollution_chains,
            "correction_pairs": correction_pairs,
            "metrics": {
                "polluted_memory_count": len(
                    [r for r in audit_results if r.verdict in {"auto_correctable", "needs_review"}]
                ),
                "pollution_chain_count": len(pollution_chains),
                "correction_count": len(correction_pairs),
                "post_edit_recurrence_count": self.count_post_edit_recurrence(correction_pairs),
            },
        }

    def save_report(self, output_file: str) -> Dict[str, Any]:
        report = self.build_report()
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=False, indent=2)
        return report

    def memory_counts(self) -> Dict[str, int]:
        data = self.memory.memory
        return {
            "raw_dialogue_log": len(data.get("raw_dialogue_log", [])),
            "memory_candidates": len(data.get("memory_candidates", [])),
            "committed_memories": len(data.get("committed_memories", [])),
            "active_committed_memories": len(
                [item for item in data.get("committed_memories", []) if item.get("status") == "active"]
            ),
            "inactive_committed_memories": len(
                [item for item in data.get("committed_memories", []) if item.get("status") == "inactive"]
            ),
        }

    def audit_summary(self, audit_results: List[AuditResult]) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for result in audit_results:
            summary[result.verdict] = summary.get(result.verdict, 0) + 1
        return summary

    def find_pollution_chains(self, audit_by_id: Dict[str, AuditResult]) -> List[Dict[str, Any]]:
        chains = []
        conversations = self.memory.memory.get("conversations", [])
        conversation_index = {
            item.get("conversation_id"): index
            for index, item in enumerate(conversations)
        }
        candidates = self.memory.memory.get("memory_candidates", [])

        for committed in self.memory.memory.get("committed_memories", []):
            memory_id = str(committed.get("memory_id", ""))
            result = audit_by_id.get(memory_id)
            if not result or result.verdict not in {"auto_correctable", "needs_review"}:
                continue
            source_conversation = committed.get("conversation_id")
            source_index = conversation_index.get(source_conversation, -1)
            markers = self.error_markers(result)
            if not markers:
                continue

            later_candidates = []
            for candidate in candidates:
                candidate_index = conversation_index.get(candidate.get("conversation_id"), -1)
                if candidate_index <= source_index:
                    continue
                content = str(candidate.get("content", ""))
                if any(marker and marker in content for marker in markers):
                    later_candidates.append(
                        {
                            "candidate_id": candidate.get("candidate_id"),
                            "conversation_id": candidate.get("conversation_id"),
                            "agent": candidate.get("agent"),
                            "turn_id": candidate.get("turn_id"),
                            "matched_markers": [marker for marker in markers if marker in content],
                            "content": content,
                        }
                    )

            if later_candidates:
                chains.append(
                    {
                        "polluting_memory_id": memory_id,
                        "source_conversation_id": source_conversation,
                        "audit_reasons": result.reasons,
                        "later_candidates": later_candidates,
                    }
                )
        return chains

    def find_correction_pairs(self) -> List[Dict[str, Any]]:
        pairs = []
        by_id = {
            item.get("memory_id"): item
            for item in self.memory.memory.get("committed_memories", [])
        }
        for item in self.memory.memory.get("committed_memories", []):
            if item.get("memory_type") != "correction":
                continue
            for old_id in item.get("corrects", []):
                pairs.append(
                    {
                        "old_memory_id": old_id,
                        "old_status": by_id.get(old_id, {}).get("status"),
                        "correction_memory_id": item.get("memory_id"),
                        "correction_status": item.get("status"),
                        "correction_content": item.get("content"),
                    }
                )
        return pairs

    def count_post_edit_recurrence(self, correction_pairs: List[Dict[str, Any]]) -> int:
        count = 0
        candidates = self.memory.memory.get("memory_candidates", [])
        for pair in correction_pairs:
            correction_id = pair.get("correction_memory_id")
            correction = self.find_committed(correction_id)
            if not correction:
                continue
            markers = self.negative_markers(str(correction.get("content", "")))
            if not markers:
                continue
            for candidate in candidates:
                if any(marker in str(candidate.get("content", "")) for marker in markers):
                    count += 1
        return count

    def find_committed(self, memory_id: str) -> Dict[str, Any]:
        for item in self.memory.memory.get("committed_memories", []):
            if item.get("memory_id") == memory_id:
                return item
        return {}

    def error_markers(self, result: AuditResult) -> List[str]:
        markers = []
        if result.evidence:
            name = str(result.evidence.get("name", ""))
            if name:
                markers.append(name)
        for reason in result.reasons:
            if "memory contains" in reason:
                after = reason.split("memory contains", 1)[1].split(" but ", 1)[0]
                markers.extend([part.strip() for part in after.split(",") if part.strip()])
        return sorted(set(markers), key=len, reverse=True)

    def negative_markers(self, correction_content: str) -> List[str]:
        markers = []
        for word in ("不是", "错误前提", "应先纠正"):
            if word in correction_content:
                markers.append(word)
        return markers
