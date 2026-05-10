import argparse
import csv
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bronze.bronze_qa_system import (
    ARCHITECTURES,
    PEER,
    SEQUENTIAL,
    answer_question_detailed,
    initialize_bronze_system,
    safe_print,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run bronze dialogue test cases in batch.")
    parser.add_argument(
        "--tests",
        "-t",
        default="bronze_dialogue_tests.json",
        help="Path to the dialogue test JSON file.",
    )
    parser.add_argument(
        "--architecture",
        "-a",
        choices=[SEQUENTIAL, PEER],
        default=SEQUENTIAL,
        help="Multi-agent architecture to run.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="bronze_dialogue_test_results.json",
        help="Output result JSON file.",
    )
    parser.add_argument(
        "--csv-output",
        default="",
        help="Optional CSV summary output path.",
    )
    parser.add_argument(
        "--qa-output",
        default="bronze_dialogue_qa_pairs.json",
        help="Output JSON file containing only per-turn questions and final answers.",
    )
    parser.add_argument(
        "--category",
        default="",
        help="Run only cases with this test_category.",
    )
    parser.add_argument(
        "--test-id",
        action="append",
        default=[],
        help="Run only the specified test_id. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of cases to run after filtering. 0 means all.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip this many cases after filtering.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Seconds to sleep between cases to avoid API rate pressure.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and preview selected cases without calling the LLM.",
    )
    parser.add_argument(
        "--no-seed-context",
        action="store_true",
        help="Do not write system_context entries into shared memory before a case.",
    )
    parser.add_argument(
        "--rebuild-vector-db",
        action="store_true",
        help="Rebuild the FAISS index and SQLite metadata from bronze_items.json before running tests.",
    )
    return parser.parse_args()


def load_cases(path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict):
        cases = data.get("cases", [])
        if not isinstance(cases, list):
            raise ValueError("Test JSON field 'cases' must be a list.")
        return data, [case for case in cases if isinstance(case, dict)]
    if isinstance(data, list):
        return {"dataset_name": Path(path).stem}, normalize_list_cases(data)
    raise ValueError("Test JSON must be either an object with 'cases' or a list.")


def normalize_list_cases(items: List[Any]) -> List[Dict[str, Any]]:
    cases = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            cases.append(
                {
                    "test_id": f"case_{index:04d}",
                    "test_category": "adhoc",
                    "dialogue": [{"role": "user", "content": item}],
                }
            )
        elif isinstance(item, dict):
            case = dict(item)
            case.setdefault("test_id", f"case_{index:04d}")
            if "dialogue" not in case and "question" in case:
                case["dialogue"] = [{"role": "user", "content": case["question"]}]
            cases.append(case)
    return cases


def filter_cases(cases: List[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
    selected = cases
    if args.category:
        selected = [case for case in selected if case.get("test_category") == args.category]
    if args.test_id:
        wanted = set(args.test_id)
        selected = [case for case in selected if str(case.get("test_id")) in wanted]
    if args.offset:
        selected = selected[args.offset :]
    if args.limit:
        selected = selected[: args.limit]
    return selected


def user_messages(case: Dict[str, Any]) -> List[str]:
    return [
        str(item.get("content", "")).strip()
        for item in case.get("dialogue", [])
        if isinstance(item, dict) and item.get("role") == "user" and str(item.get("content", "")).strip()
    ]


def system_context_messages(case: Dict[str, Any]) -> List[str]:
    return [
        str(item.get("content", "")).strip()
        for item in case.get("dialogue", [])
        if isinstance(item, dict)
        and item.get("role") == "system_context"
        and str(item.get("content", "")).strip()
    ]


def expected_text(case: Dict[str, Any]) -> str:
    for item in case.get("dialogue", []):
        if isinstance(item, dict) and item.get("role") == "assistant_expected":
            return str(item.get("content", "")).strip()
    return ""


def seed_system_context(vector_db: Any, case: Dict[str, Any], architecture: str) -> List[str]:
    seeded_ids = []
    for index, content in enumerate(system_context_messages(case), start=1):
        seed_id = vector_db.add_memory(
            content=content,
            source_type="agent_inference",
            source_ids=[str(case.get("test_id", ""))],
            created_by="TestContextSeeder",
            created_turn=f"{case.get('test_id')}_seed_{index}",
            confidence=0.35,
            contamination_status=infer_seed_contamination_status(content),
            metadata={
                "architecture": architecture,
                "test_id": case.get("test_id"),
                "seed_index": index,
                "seed_role": "system_context",
            },
        )
        seeded_ids.append(seed_id)
    if seeded_ids:
        vector_db.save()
    return seeded_ids


def infer_seed_contamination_status(content: str) -> str:
    risk_terms = ("错误", "冲突", "不是", "contaminated", "hallucination", "M_AGENT")
    return "suspected" if any(term in content for term in risk_terms) else "unknown"


def graph_counts(vector_db: Any) -> Dict[str, int]:
    rows = vector_db.conn.execute(
        "SELECT edge_type, COUNT(*) AS count FROM graph_edges GROUP BY edge_type"
    ).fetchall()
    return {str(row["edge_type"]): int(row["count"]) for row in rows}


def table_count(vector_db: Any, table_name: str) -> int:
    return int(vector_db.conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()["count"])


def get_new_logs(vector_db: Any, before: Dict[str, int]) -> Dict[str, Any]:
    return {
        "retrieval_log_count": table_count(vector_db, "retrieval_log") - before["retrieval_log"],
        "usage_log_count": table_count(vector_db, "usage_log") - before["usage_log"],
        "graph_edge_count": table_count(vector_db, "graph_edges") - before["graph_edges"],
        "verifier_log_count": table_count(vector_db, "verifier_log") - before["verifier_log"],
    }


def snapshot_counts(vector_db: Any) -> Dict[str, int]:
    return {
        "retrieval_log": table_count(vector_db, "retrieval_log"),
        "usage_log": table_count(vector_db, "usage_log"),
        "graph_edges": table_count(vector_db, "graph_edges"),
        "verifier_log": table_count(vector_db, "verifier_log"),
    }


def recent_retrieved_memory_ids(vector_db: Any, before_count: int) -> List[str]:
    rows = vector_db.conn.execute(
        """
        SELECT retrieved_memory_ids FROM retrieval_log
        ORDER BY created_at ASC
        LIMIT -1 OFFSET ?
        """,
        (before_count,),
    ).fetchall()
    memory_ids: List[str] = []
    for row in rows:
        memory_ids.extend(load_json_list(row["retrieved_memory_ids"]))
    return dedupe(memory_ids)


def rows_after_count(vector_db: Any, table_name: str, before_count: int) -> List[Dict[str, Any]]:
    rows = vector_db.conn.execute(
        f"SELECT * FROM {table_name} ORDER BY created_at ASC LIMIT -1 OFFSET ?",
        (before_count,),
    ).fetchall()
    return [decode_row(dict(row)) for row in rows]


def decode_row(row: Dict[str, Any]) -> Dict[str, Any]:
    for key in (
        "retrieved_memory_ids",
        "used_memory_ids",
        "distances",
        "metadata",
        "source_ids",
        "derived_from",
        "reasons",
    ):
        if key in row:
            row[key] = maybe_json(row[key])
    return row


def maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def memory_details(vector_db: Any, memory_ids: Iterable[str]) -> List[Dict[str, Any]]:
    details = []
    for memory_id in dedupe(str(item) for item in memory_ids if item):
        memory = vector_db.get_memory(memory_id)
        if not memory:
            continue
        details.append(
            {
                "memory_id": memory.get("memory_id"),
                "source_type": memory.get("source_type"),
                "source_ids": memory.get("source_ids", []),
                "created_by": memory.get("created_by"),
                "created_turn": memory.get("created_turn"),
                "confidence": memory.get("confidence"),
                "contamination_status": memory.get("contamination_status"),
                "derived_from": memory.get("derived_from", []),
                "content": memory.get("content"),
                "metadata": memory.get("metadata", {}),
            }
        )
    return details


def kb_ids_from_memory_details(details: List[Dict[str, Any]]) -> List[str]:
    kb_ids = []
    for item in details:
        for source_id in item.get("source_ids", []):
            source_id = str(source_id)
            if source_id.startswith("KB_"):
                kb_ids.append(source_id)
    return dedupe(kb_ids)


def compact_agent_history(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    compact = []
    for index, message in enumerate(history, start=1):
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        compact.append(
            {
                "index": index,
                "agent": str(message.get("name") or message.get("role") or "unknown"),
                "role": str(message.get("role") or ""),
                "content": content,
            }
        )
    return compact


def build_turn_json_log(
    *,
    test_id: str,
    test_category: str,
    turn_index: int,
    answer_detail: Dict[str, Any],
    before: Dict[str, int],
    after: Dict[str, int],
    vector_db: Any,
) -> Dict[str, Any]:
    retrieval_rows = rows_after_count(vector_db, "retrieval_log", before["retrieval_log"])
    usage_rows = rows_after_count(vector_db, "usage_log", before["usage_log"])
    graph_edge_rows = rows_after_count(vector_db, "graph_edges", before["graph_edges"])
    verifier_rows = rows_after_count(vector_db, "verifier_log", before["verifier_log"])

    retrieved_ids = dedupe(
        list(answer_detail.get("retrieved_memory_ids", []))
        + [memory_id for row in retrieval_rows for memory_id in row.get("retrieved_memory_ids", [])]
    )
    used_ids = dedupe(
        list(answer_detail.get("used_memory_ids", []))
        + [memory_id for row in usage_rows for memory_id in row.get("used_memory_ids", [])]
    )
    derived_from = list(answer_detail.get("derived_from", []))
    retrieved_details = memory_details(vector_db, retrieved_ids)
    used_details = memory_details(vector_db, used_ids)

    return {
        "test_id": test_id,
        "test_category": test_category,
        "turn_index": turn_index,
        "turn_id": answer_detail.get("turn_id"),
        "question": answer_detail.get("question"),
        "final_answer_agent": answer_detail.get("final_answer_agent"),
        "final_answer": answer_detail.get("final_answer"),
        "audit_text": answer_detail.get("audit_text"),
        "agent_dialogue": compact_agent_history(answer_detail.get("raw_agent_history", [])),
        "retrieval": {
            "retrieved_memory_ids": retrieved_ids,
            "retrieved_kb_ids": kb_ids_from_memory_details(retrieved_details),
            "retrieved_memory_details": retrieved_details,
            "retrieval_log_rows": retrieval_rows,
        },
        "usage": {
            "used_memory_ids": used_ids,
            "used_kb_ids": kb_ids_from_memory_details(used_details),
            "used_memory_details": used_details,
            "derived_from": derived_from,
            "usage_log_rows": usage_rows,
        },
        "graph_edges_created": graph_edge_rows,
        "verifier_log_rows": verifier_rows,
        "counts_before": before,
        "counts_after": after,
        "new_log_counts": get_new_logs(vector_db, before),
    }


def recent_used_memory_ids(vector_db: Any, before_count: int) -> List[str]:
    rows = vector_db.conn.execute(
        """
        SELECT used_memory_ids FROM usage_log
        ORDER BY created_at ASC
        LIMIT -1 OFFSET ?
        """,
        (before_count,),
    ).fetchall()
    memory_ids: List[str] = []
    for row in rows:
        memory_ids.extend(load_json_list(row["used_memory_ids"]))
    return dedupe(memory_ids)


def load_json_list(value: str) -> List[str]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def evaluate_case(case: Dict[str, Any], final_answer: str, retrieved_ids: List[str], used_ids: List[str]) -> Dict[str, Any]:
    expected_assertions = [str(item) for item in case.get("expected_assertions", [])]
    assertion_hits = {
        assertion: bool(assertion and assertion in final_answer)
        for assertion in expected_assertions
    }
    graph_expectation = case.get("memory_graph_expectation", {})
    must_retrieve_kb_ids = graph_expectation.get("must_retrieve_kb_ids", []) if isinstance(graph_expectation, dict) else []
    return {
        "assertion_hits": assertion_hits,
        "assertion_pass_rate": (
            sum(1 for passed in assertion_hits.values() if passed) / len(assertion_hits)
            if assertion_hits
            else None
        ),
        "has_usage_log": bool(used_ids),
        "retrieved_memory_count": len(retrieved_ids),
        "used_memory_count": len(used_ids),
        "must_retrieve_kb_ids": must_retrieve_kb_ids,
    }


def run_case(
    case: Dict[str, Any],
    *,
    architecture: str,
    vector_db: Any,
    memory: Any,
    seed_context: bool,
) -> Dict[str, Any]:
    test_id = str(case.get("test_id", "unknown"))
    seeded_memory_ids = seed_system_context(vector_db, case, architecture) if seed_context else []
    messages = user_messages(case)
    before = snapshot_counts(vector_db)
    started = time.time()

    turns = []
    turn_logs = []
    final_answer = ""
    audit_text = ""
    error = ""
    try:
        for turn_index, message in enumerate(messages, start=1):
            turn_before = snapshot_counts(vector_db)
            answer_detail = answer_question_detailed(architecture, message, vector_db, memory)
            turn_after = snapshot_counts(vector_db)
            final_answer = str(answer_detail.get("final_answer", ""))
            audit_text = str(answer_detail.get("audit_text", ""))
            turn_log = build_turn_json_log(
                test_id=test_id,
                test_category=str(case.get("test_category", "")),
                turn_index=turn_index,
                answer_detail=answer_detail,
                before=turn_before,
                after=turn_after,
                vector_db=vector_db,
            )
            turn_logs.append(turn_log)
            turns.append(
                {
                    "turn_index": turn_index,
                    "user_message": message,
                    "final_answer_agent": answer_detail.get("final_answer_agent", ""),
                    "turn_id": answer_detail.get("turn_id", ""),
                    "final_answer": final_answer,
                    "audit_text": audit_text,
                }
            )
    except Exception as exc:
        error = str(exc)

    elapsed = time.time() - started
    after = snapshot_counts(vector_db)
    retrieved_ids = recent_retrieved_memory_ids(vector_db, before["retrieval_log"])
    used_ids = recent_used_memory_ids(vector_db, before["usage_log"])

    return {
        "test_id": test_id,
        "test_category": case.get("test_category", ""),
        "difficulty": case.get("difficulty"),
        "hallucination_risk": case.get("hallucination_risk", ""),
        "target_item_ids": case.get("target_item_ids", []),
        "seeded_memory_ids": seeded_memory_ids,
        "turns": turns,
        "turn_logs": turn_logs,
        "final_answer": final_answer,
        "audit_text": audit_text,
        "expected_answer": expected_text(case),
        "evaluation": evaluate_case(case, final_answer, retrieved_ids, used_ids),
        "retrieved_memory_ids": retrieved_ids,
        "used_memory_ids": used_ids,
        "new_log_counts": get_new_logs(vector_db, before),
        "graph_counts_after": graph_counts(vector_db),
        "error": error,
        "elapsed_seconds": round(elapsed, 3),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "counts_before": before,
        "counts_after": after,
    }


def write_json(path: str, payload: Dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def write_csv(path: str, results: List[Dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "test_id",
                "test_category",
                "difficulty",
                "hallucination_risk",
                "assertion_pass_rate",
                "retrieved_memory_count",
                "used_memory_count",
                "retrieval_log_count",
                "usage_log_count",
                "graph_edge_count",
                "verifier_log_count",
                "elapsed_seconds",
                "error",
            ],
        )
        writer.writeheader()
        for result in results:
            evaluation = result.get("evaluation", {})
            logs = result.get("new_log_counts", {})
            writer.writerow(
                {
                    "test_id": result.get("test_id"),
                    "test_category": result.get("test_category"),
                    "difficulty": result.get("difficulty"),
                    "hallucination_risk": result.get("hallucination_risk"),
                    "assertion_pass_rate": evaluation.get("assertion_pass_rate"),
                    "retrieved_memory_count": evaluation.get("retrieved_memory_count"),
                    "used_memory_count": evaluation.get("used_memory_count"),
                    "retrieval_log_count": logs.get("retrieval_log_count"),
                    "usage_log_count": logs.get("usage_log_count"),
                    "graph_edge_count": logs.get("graph_edge_count"),
                    "verifier_log_count": logs.get("verifier_log_count"),
                    "elapsed_seconds": result.get("elapsed_seconds"),
                    "error": result.get("error"),
                }
            )


def extract_qa_pairs(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pairs = []
    for result in results:
        for turn in result.get("turns", []):
            pairs.append(
                {
                    "test_id": result.get("test_id"),
                    "test_category": result.get("test_category"),
                    "turn_index": turn.get("turn_index"),
                    "turn_id": turn.get("turn_id"),
                    "question": turn.get("user_message"),
                    "final_answer_agent": turn.get("final_answer_agent"),
                    "final_answer": turn.get("final_answer"),
                }
            )
    return pairs


def main() -> None:
    args = parse_args()
    metadata, cases = load_cases(args.tests)
    selected_cases = filter_cases(cases, args)

    safe_print(f"Loaded {len(cases)} cases from {args.tests}.")
    safe_print(f"Selected {len(selected_cases)} cases for architecture={args.architecture}.")

    if args.dry_run:
        preview = {
            "dataset": metadata.get("dataset_name", ""),
            "selected_count": len(selected_cases),
            "test_ids": [case.get("test_id") for case in selected_cases],
            "categories": sorted({str(case.get("test_category", "")) for case in selected_cases}),
        }
        write_json(args.output, preview)
        safe_print(f"Dry-run preview written: {args.output}")
        return

    vector_db, memory = initialize_bronze_system(
        args.architecture,
        rebuild_vector_db=args.rebuild_vector_db,
    )
    results = []

    for index, case in enumerate(selected_cases, start=1):
        safe_print(f"[{index}/{len(selected_cases)}] Running {case.get('test_id')}")
        result = run_case(
            case,
            architecture=args.architecture,
            vector_db=vector_db,
            memory=memory,
            seed_context=not args.no_seed_context,
        )
        results.append(result)
        if result.get("error"):
            safe_print(f"  error: {result['error']}")
        else:
            safe_print(
                "  done: "
                f"retrieved={len(result['retrieved_memory_ids'])}, "
                f"used={len(result['used_memory_ids'])}, "
                f"edges+={result['new_log_counts']['graph_edge_count']}"
            )
        if args.sleep > 0 and index < len(selected_cases):
            time.sleep(args.sleep)

    payload = {
        "dataset": {
            "name": metadata.get("dataset_name", ""),
            "source_file": metadata.get("source_file", ""),
            "case_count": metadata.get("case_count", len(cases)),
        },
        "architecture": args.architecture,
        "architecture_label": ARCHITECTURES[args.architecture]["label"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selected_count": len(selected_cases),
        "results": results,
    }
    write_json(args.output, payload)
    if args.csv_output:
        write_csv(args.csv_output, results)
    if args.qa_output:
        write_json(
            args.qa_output,
            {
                "generated_at": payload["generated_at"],
                "architecture": args.architecture,
                "source_result_file": args.output,
                "qa_pairs": extract_qa_pairs(results),
            },
        )
    vector_db.save()

    safe_print(f"JSON results written: {args.output}")
    if args.csv_output:
        safe_print(f"CSV summary written: {args.csv_output}")
    if args.qa_output:
        safe_print(f"QA pairs written: {args.qa_output}")


if __name__ == "__main__":
    main()
