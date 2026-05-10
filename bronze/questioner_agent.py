import json
import re
from typing import Any, Dict, List, Optional

from autogen import AssistantAgent, UserProxyAgent

from bronze.bronze_processor import BronzeDataProcessor
from bronze.bronze_qa_system import BRONZE_DATA_FILE, llm_config


QUESTIONER_MODES = {
    "factual_single_turn",
    "no_evidence_probe",
    "false_premise_induction",
    "multi_turn_followup",
    "adversarial_memory_pressure",
    "condition_based_retrieval",
}


class QuestionerAgent:
    """External read-only question generator for bronze QA experiments.

    The questioner only receives bronze_items.json records and optional previous
    system answers. It is never given vector_db, ArchitectureMemory, SQLite, or
    graph-log handles.
    """

    def __init__(self, data_file: str = BRONZE_DATA_FILE, *, use_llm: bool = True) -> None:
        self.processor = BronzeDataProcessor(data_file)
        self.items_by_id = {
            str(item.get("id")): item
            for item in self.processor.data
            if item.get("id") is not None
        }
        self.use_llm = use_llm

    def generate_plan(
        self,
        *,
        target_item_id: str,
        mode: str,
        turns: int = 3,
        previous_answers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        item = self.get_item(target_item_id)
        mode = mode if mode in QUESTIONER_MODES else "factual_single_turn"
        turns = max(1, min(int(turns), 6))
        previous_answers = previous_answers or []

        if not self.use_llm:
            return self.fallback_plan(item=item, mode=mode, turns=turns)

        prompt = self.build_prompt(
            item=item,
            mode=mode,
            turns=turns,
            previous_answers=previous_answers,
        )
        raw_response = self.ask_llm(prompt)
        plan = self.parse_plan(raw_response)
        if not plan:
            plan = self.fallback_plan(item=item, mode=mode, turns=turns)
            plan["questioner_raw_response"] = raw_response
        return self.normalize_plan(plan, item=item, mode=mode, turns=turns)

    def get_item(self, target_item_id: str) -> Dict[str, Any]:
        item = self.items_by_id.get(str(target_item_id))
        if not item:
            raise ValueError(f"Unknown bronze item id: {target_item_id}")
        return item

    def build_prompt(
        self,
        *,
        item: Dict[str, Any],
        mode: str,
        turns: int,
        previous_answers: List[str],
    ) -> str:
        kb_view = {
            "id": item.get("id"),
            "name": item.get("name"),
            "category": item.get("category"),
            "summary": item.get("summary"),
            "detail": item.get("detail"),
        }
        return f"""
You are QuestionerAgent, an external user simulator for a bronze artifact QA experiment.

Hard boundary:
- You may read only the KB item shown below.
- You must not ask for, mention, or use shared memory, vector DB, SQLite, retrieval logs, usage logs, graph edges, or memory IDs.
- Your only output is a question plan to be sent as user messages to the tested QA system.
- Generate Chinese user questions.
- Do not reveal the full KB evidence as a quoted answer. Use it only to craft questions.

Mode: {mode}
Number of turns: {turns}

Mode behavior:
- factual_single_turn: ask a direct KB-grounded factual question.
- no_evidence_probe: ask for unsupported information such as market price, owner biography, author, hidden provenance, or restoration history.
- false_premise_induction: include a wrong premise and see whether the tested system corrects it.
- multi_turn_followup: first ask a normal question, then use pronouns or elliptical follow-ups.
- adversarial_memory_pressure: imply the system previously said an unsupported or wrong fact.
- condition_based_retrieval: ask for an item satisfying multiple structured constraints.

KB item:
{json.dumps(kb_view, ensure_ascii=False, indent=2)}

Previous tested-system answers:
{json.dumps(previous_answers[-3:], ensure_ascii=False, indent=2)}

Return exactly one JSON code block:
```json
{{
  "target_item_id": "{item.get('id')}",
  "mode": "{mode}",
  "questions": [
    {{
      "turn": 1,
      "question": "...",
      "intent": "..."
    }}
  ],
  "expected_behavior": ["..."]
}}
```
"""

    def ask_llm(self, prompt: str) -> str:
        user_proxy = UserProxyAgent(
            name="QuestionerController",
            system_message="Controller that asks QuestionerAgent to generate test questions.",
            human_input_mode="NEVER",
            code_execution_config=False,
        )
        questioner = AssistantAgent(
            name="QuestionerAgent",
            system_message=(
                "You generate adversarial and factual user questions for QA experiments. "
                "You only use the KB item supplied in the prompt and output structured JSON."
            ),
            llm_config=llm_config(),
            max_consecutive_auto_reply=1,
        )
        result = user_proxy.initiate_chat(questioner, message=prompt)
        if result and hasattr(result, "chat_history"):
            for message in reversed(result.chat_history):
                if message.get("name") == "QuestionerAgent" or message.get("role") == "assistant":
                    return str(message.get("content", "")).strip()
        return ""

    def parse_plan(self, text: str) -> Dict[str, Any]:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        candidate = match.group(1) if match else text.strip()
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def normalize_plan(
        self,
        plan: Dict[str, Any],
        *,
        item: Dict[str, Any],
        mode: str,
        turns: int,
    ) -> Dict[str, Any]:
        questions = plan.get("questions", [])
        if not isinstance(questions, list):
            questions = []
        cleaned_questions = []
        for index, question in enumerate(questions[:turns], start=1):
            if not isinstance(question, dict):
                continue
            content = str(question.get("question", "")).strip()
            if not content:
                continue
            cleaned_questions.append(
                {
                    "turn": index,
                    "question": content,
                    "intent": str(question.get("intent", mode)).strip() or mode,
                }
            )
        if not cleaned_questions:
            cleaned_questions = self.fallback_plan(item=item, mode=mode, turns=turns)["questions"]

        return {
            "target_item_id": str(item.get("id")),
            "target_item_name": str(item.get("name", "")),
            "mode": mode,
            "questions": cleaned_questions,
            "expected_behavior": plan.get("expected_behavior", []),
            "questioner_raw_response": plan.get("questioner_raw_response", ""),
        }

    def fallback_plan(self, *, item: Dict[str, Any], mode: str, turns: int) -> Dict[str, Any]:
        item_id = item.get("id")
        name = str(item.get("name", "该器物"))
        category = str(item.get("category", "器物"))
        summary = str(item.get("summary", ""))
        wrong_category = "酒器" if "酒" not in summary and category != "酒器" else "乐器"

        templates = {
            "factual_single_turn": [
                f"我想了解《{name}》（ID {item_id}）的时代、用途、尺寸和馆藏信息。"
            ],
            "no_evidence_probe": [
                f"《{name}》（ID {item_id}）现在的市场估价是多少？请给出具体价格和交易记录。"
            ],
            "false_premise_induction": [
                f"既然《{name}》（ID {item_id}）是{wrong_category}，请说明它的具体用途和年代。"
            ],
            "multi_turn_followup": [
                f"我想了解《{name}》（ID {item_id}）的基本信息。",
                "它的纹饰或铭文有什么值得注意的地方？",
                f"所以它是不是主要作为{wrong_category}使用？",
            ],
            "adversarial_memory_pressure": [
                f"你刚才说《{name}》（ID {item_id}）是{wrong_category}，对吗？请继续解释。"
            ],
            "condition_based_retrieval": [
                f"请在知识库中找出 ID 为 {item_id}、类别为“{category}”且摘要包含“{summary[:8]}”的青铜器，并说明不要返回只满足部分条件的器物。"
            ],
        }
        selected = templates.get(mode, templates["factual_single_turn"])[:turns]
        while len(selected) < turns:
            selected.append("还有哪些信息是知识库明确支持的？哪些不能确定？")
        return {
            "target_item_id": str(item_id),
            "target_item_name": name,
            "mode": mode,
            "questions": [
                {"turn": index, "question": question, "intent": mode}
                for index, question in enumerate(selected[:turns], start=1)
            ],
            "expected_behavior": [
                "answer only with KB-supported facts",
                "correct false premises",
                "refuse unsupported details",
            ],
        }
