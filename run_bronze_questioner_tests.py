import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from bronze.bronze_qa_system import (
    ARCHITECTURES,
    PEER,
    SEQUENTIAL,
    answer_question,
    initialize_bronze_system,
    safe_print,
)
from bronze.questioner_agent import QUESTIONER_MODES, QuestionerAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run QA experiments driven by an external read-only QuestionerAgent."
    )
    parser.add_argument("--target-id", required=True, help="Bronze KB item id, e.g. 364542.")
    parser.add_argument(
        "--mode",
        choices=sorted(QUESTIONER_MODES),
        default="multi_turn_followup",
        help="Question generation mode.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=3,
        help="Number of user turns to generate.",
    )
    parser.add_argument(
        "--architecture",
        "-a",
        choices=[SEQUENTIAL, PEER],
        default=PEER,
        help="Tested bronze QA architecture.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="bronze_questioner_test_result.json",
        help="Output JSON file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the question plan without calling the tested QA system.",
    )
    parser.add_argument(
        "--no-llm-questioner",
        action="store_true",
        help="Use deterministic template questions instead of calling the QuestionerAgent LLM.",
    )
    parser.add_argument(
        "--dynamic-followup",
        action="store_true",
        help="Regenerate each next question after observing previous tested-system answers.",
    )
    parser.add_argument(
        "--rebuild-vector-db",
        action="store_true",
        help="Rebuild the tested system vector DB before running.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between tested-system turns.",
    )
    return parser.parse_args()


def write_json(path: str, payload: Dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def run_static_plan(
    *,
    plan: Dict[str, Any],
    architecture: str,
    vector_db: Any,
    memory: Any,
    sleep_seconds: float,
) -> List[Dict[str, Any]]:
    turns = []
    for question in plan["questions"]:
        user_message = question["question"]
        started = time.time()
        answer, audit = answer_question(architecture, user_message, vector_db, memory)
        turns.append(
            {
                "turn": question["turn"],
                "intent": question.get("intent", ""),
                "user_message": user_message,
                "final_answer": answer,
                "audit_text": audit,
                "elapsed_seconds": round(time.time() - started, 3),
            }
        )
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    return turns


def run_dynamic_plan(
    *,
    questioner: QuestionerAgent,
    target_id: str,
    mode: str,
    turns: int,
    architecture: str,
    vector_db: Any,
    memory: Any,
    sleep_seconds: float,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    observed_answers: List[str] = []
    generated_questions: List[Dict[str, Any]] = []
    turn_results: List[Dict[str, Any]] = []
    base_plan: Dict[str, Any] = {}

    for turn_index in range(1, turns + 1):
        plan = questioner.generate_plan(
            target_item_id=target_id,
            mode=mode,
            turns=1,
            previous_answers=observed_answers,
        )
        if not base_plan:
            base_plan = dict(plan)
        question = dict(plan["questions"][0])
        question["turn"] = turn_index
        generated_questions.append(question)

        started = time.time()
        answer, audit = answer_question(architecture, question["question"], vector_db, memory)
        observed_answers.append(answer)
        turn_results.append(
            {
                "turn": turn_index,
                "intent": question.get("intent", ""),
                "user_message": question["question"],
                "final_answer": answer,
                "audit_text": audit,
                "elapsed_seconds": round(time.time() - started, 3),
            }
        )
        if sleep_seconds > 0 and turn_index < turns:
            time.sleep(sleep_seconds)

    base_plan["questions"] = generated_questions
    return base_plan, turn_results


def main() -> None:
    args = parse_args()
    questioner = QuestionerAgent(use_llm=not args.no_llm_questioner)

    if args.dynamic_followup:
        initial_plan = questioner.generate_plan(
            target_item_id=args.target_id,
            mode=args.mode,
            turns=1,
        )
    else:
        initial_plan = questioner.generate_plan(
            target_item_id=args.target_id,
            mode=args.mode,
            turns=args.turns,
        )

    payload: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "architecture": args.architecture,
        "architecture_label": ARCHITECTURES[args.architecture]["label"],
        "questioner_boundaries": {
            "can_read": ["bronze_items.json", "previous tested-system answers"],
            "cannot_read_or_write": [
                "vector_db",
                "metadata.sqlite3",
                "bronze_memory_*.json",
                "retrieval_log",
                "usage_log",
                "graph_edges",
            ],
        },
        "dry_run": args.dry_run,
        "dynamic_followup": args.dynamic_followup,
        "question_plan": initial_plan,
        "turns": [],
    }

    if args.dry_run:
        write_json(args.output, payload)
        safe_print(f"Questioner dry-run plan written: {args.output}")
        return

    vector_db, memory = initialize_bronze_system(
        args.architecture,
        rebuild_vector_db=args.rebuild_vector_db,
    )

    if args.dynamic_followup:
        final_plan, turns = run_dynamic_plan(
            questioner=questioner,
            target_id=args.target_id,
            mode=args.mode,
            turns=args.turns,
            architecture=args.architecture,
            vector_db=vector_db,
            memory=memory,
            sleep_seconds=args.sleep,
        )
        payload["question_plan"] = final_plan
        payload["turns"] = turns
    else:
        payload["turns"] = run_static_plan(
            plan=initial_plan,
            architecture=args.architecture,
            vector_db=vector_db,
            memory=memory,
            sleep_seconds=args.sleep,
        )

    vector_db.save()
    write_json(args.output, payload)
    safe_print(f"Questioner test result written: {args.output}")


if __name__ == "__main__":
    main()
