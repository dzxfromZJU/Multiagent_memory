import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from bronze.bronze_processor import BronzeDataProcessor


QUESTION_TEMPLATES = [
    "请根据知识库介绍《{name}》（ID {id}）的时代、器类和基本用途。",
    "《{name}》（ID {id}）有哪些尺寸或重量信息？",
    "《{name}》（ID {id}）的纹饰、铭文或形制特征是什么？",
    "《{name}》（ID {id}）的出土地点或馆藏信息是什么？",
    "请只依据知识库概括《{name}》（ID {id}）的关键信息，不要补充未记录内容。",
    "如果知识库没有记载《{name}》（ID {id}）的某些信息，请明确说明缺失。",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate long factual bronze dialogue tests with 10+ user questions per case."
    )
    parser.add_argument(
        "--source",
        default="bronze_items.json",
        help="Read-only bronze item JSON file.",
    )
    parser.add_argument(
        "--output",
        default="bronze_long_fqa_tests.json",
        help="Output test JSON file.",
    )
    parser.add_argument(
        "--case-count",
        type=int,
        default=20,
        help="Number of long dialogue cases to generate.",
    )
    parser.add_argument(
        "--questions-per-case",
        type=int,
        default=12,
        help="Number of user questions in each dialogue case. Must be at least 10.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start offset in bronze_items.json after filtering valid records.",
    )
    parser.add_argument(
        "--items-per-case",
        type=int,
        default=4,
        help="How many bronze artifacts each long dialogue should cover.",
    )
    return parser.parse_args()


def valid_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        item
        for item in items
        if item.get("id") is not None and str(item.get("name", "")).strip()
    ]


def item_assertions(item: Dict[str, Any]) -> List[str]:
    assertions = [str(item.get("name", "")).strip()]
    category = str(item.get("category", "")).strip()
    if category:
        assertions.append(category)
    return assertions


def make_question(item: Dict[str, Any], question_index: int) -> str:
    template = QUESTION_TEMPLATES[question_index % len(QUESTION_TEMPLATES)]
    return template.format(
        id=item.get("id"),
        name=str(item.get("name", "")).strip(),
    )


def build_case(
    *,
    case_index: int,
    items: List[Dict[str, Any]],
    questions_per_case: int,
) -> Dict[str, Any]:
    dialogue = []
    target_ids = [int(item["id"]) for item in items if str(item.get("id", "")).isdigit()]
    expected_assertions = []

    for question_index in range(questions_per_case):
        item = items[question_index % len(items)]
        dialogue.append(
            {
                "role": "user",
                "content": make_question(item, question_index),
            }
        )
        expected_assertions.extend(item_assertions(item))

    return {
        "test_id": f"LFQA_{case_index:03d}",
        "test_category": "factual_long_dialogue",
        "goal": "生成正常事实型长对话资料，观察多轮共享记忆读写和事实回答稳定性。",
        "difficulty": 2,
        "target_item_ids": target_ids,
        "dialogue": dialogue,
        "expected_assertions": sorted(set(expected_assertions)),
        "hallucination_risk": "低",
        "memory_graph_expectation": {
            "must_retrieve_kb_ids": [f"KB_{item_id}" for item_id in target_ids],
            "must_cite_or_use_memory_ids": [],
            "forbid_write_unverified_memory": False,
            "expected_edges": ["retrieved", "cited", "written_by"],
        },
        "evaluation_tags": ["事实问答", "长对话", "正常询问", "来源约束"],
    }


def generate_cases(
    items: List[Dict[str, Any]],
    *,
    case_count: int,
    questions_per_case: int,
    items_per_case: int,
    start: int,
) -> List[Dict[str, Any]]:
    if questions_per_case < 10:
        raise ValueError("--questions-per-case must be at least 10.")
    if items_per_case < 1:
        raise ValueError("--items-per-case must be at least 1.")

    usable = valid_items(items)
    if not usable:
        raise ValueError("No valid bronze items found.")

    cases = []
    cursor = start % len(usable)
    for case_index in range(1, case_count + 1):
        case_items = [
            usable[(cursor + offset) % len(usable)]
            for offset in range(items_per_case)
        ]
        cases.append(
            build_case(
                case_index=case_index,
                items=case_items,
                questions_per_case=questions_per_case,
            )
        )
        cursor = (cursor + items_per_case) % len(usable)
    return cases


def main() -> None:
    args = parse_args()
    processor = BronzeDataProcessor(args.source)
    cases = generate_cases(
        processor.data,
        case_count=args.case_count,
        questions_per_case=args.questions_per_case,
        items_per_case=args.items_per_case,
        start=args.start,
    )

    payload = {
        "dataset_name": "bronze_long_factual_dialogue_tests",
        "source_file": args.source,
        "source_record_count": len(processor.data),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "schema": {
            "test_category": "factual_long_dialogue",
            "dialogue": "Each case contains 10 or more factual user questions.",
        },
        "cases": cases,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(f"Generated {len(cases)} long FQA cases: {args.output}")
    print(f"Questions per case: {args.questions_per_case}")


if __name__ == "__main__":
    main()
