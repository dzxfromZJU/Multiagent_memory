import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


CORRECTION_MARKERS = [
    "不符",
    "并非",
    "不是",
    "错误",
    "纠正",
    "修正",
    "应为",
    "实际",
    "知识库记载",
    "根据知识库",
    "而不是",
    "矛盾",
    "冲突",
]

MISSING_MARKERS = ["未记载", "没有记载", "资料不足", "无法确认", "不能确定", "无依据"]


def run_comparison(
    *,
    task: str,
    cases_path: str,
    baseline_path: str,
    edited_path: str,
    json_output: str,
    csv_output: str,
    markdown_output: str,
) -> Dict[str, Any]:
    cases = cases_by_id(cases_path)
    baseline = results_by_id(baseline_path)
    edited = results_by_id(edited_path)
    rows = []
    for test_id in sorted(set(cases) | set(baseline) | set(edited)):
        case = cases.get(test_id, {})
        base_result = baseline.get(test_id, {})
        edited_result = edited.get(test_id, {})
        row = {
            "test_id": test_id,
            "task": task,
            "target_item_ids": ",".join(str(x) for x in case.get("target_item_ids", [])),
            "source_row_count": case.get("source_row_count", ""),
            "baseline_valid": is_valid(base_result),
            "edited_valid": is_valid(edited_result),
            "baseline_error": str(base_result.get("error", "")),
            "edited_error": str(edited_result.get("error", "")),
            "baseline_turn_count": len(base_result.get("turns", []) or []),
            "edited_turn_count": len(edited_result.get("turns", []) or []),
            "baseline_answer_length": len(all_answers(base_result)),
            "edited_answer_length": len(all_answers(edited_result)),
            "edited_curated_turn_count": curated_turn_count(edited_result),
            "edited_curated_fact_count": curated_fact_count(edited_result),
            "baseline_write_edge_count": edge_count(base_result, {"written_by", "derived_from"}),
            "edited_write_edge_count": edge_count(edited_result, {"written_by", "derived_from"}),
            "baseline_contradict_edge_count": edge_count(base_result, {"contradicted_by", "contradicts"}),
            "edited_contradict_edge_count": edge_count(edited_result, {"contradicted_by", "contradicts"}),
            "baseline_repair_edge_count": edge_count(base_result, {"repairs", "deprecated_by"}),
            "edited_repair_edge_count": edge_count(edited_result, {"repairs", "deprecated_by"}),
            "answer_delta": answer_delta(all_answers(base_result), all_answers(edited_result)),
        }
        row.update(task_specific_scores(task, case, base_result, prefix="baseline"))
        row.update(task_specific_scores(task, case, edited_result, prefix="edited"))
        row.update(delta_scores(row, task))
        rows.append(row)

    payload = {"task": task, "summary": summarize(rows, task), "rows": rows}
    write_json(json_output, payload)
    write_csv(csv_output, rows)
    write_markdown(markdown_output, payload)
    return payload


def load_json(path: str) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def cases_by_id(path: str) -> Dict[str, Dict[str, Any]]:
    data = load_json(path)
    return {
        str(item.get("test_id")): item
        for item in data.get("cases", [])
        if isinstance(item, dict) and item.get("test_id")
    }


def results_by_id(path: str) -> Dict[str, Dict[str, Any]]:
    data = load_json(path)
    return {
        str(item.get("test_id")): item
        for item in data.get("results", [])
        if isinstance(item, dict) and item.get("test_id")
    }


def is_valid(result: Dict[str, Any]) -> bool:
    return bool(result) and not result.get("error") and bool(result.get("turns"))


def all_answers(result: Dict[str, Any]) -> str:
    parts = []
    for turn in result.get("turns", []) or []:
        text = str(turn.get("final_answer", "")).strip()
        if text:
            parts.append(text)
    if not parts:
        text = str(result.get("final_answer", "")).strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def final_answer(result: Dict[str, Any]) -> str:
    return str(result.get("final_answer", "")).strip()


def turn_logs(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item for item in result.get("turn_logs", []) if isinstance(item, dict)]


def curated_turn_count(result: Dict[str, Any]) -> int:
    return sum(1 for log in turn_logs(result) if log.get("curated_knowledge", {}).get("curated_facts"))


def curated_fact_count(result: Dict[str, Any]) -> int:
    return sum(
        len(log.get("curated_knowledge", {}).get("curated_facts", []))
        for log in turn_logs(result)
    )


def edge_count(result: Dict[str, Any], edge_types: Iterable[str]) -> int:
    wanted = set(edge_types)
    count = 0
    for log in turn_logs(result):
        for edge in log.get("graph_edges_created", []) or []:
            if str(edge.get("edge_type")) in wanted:
                count += 1
    return count


def answer_delta(baseline: str, edited: str) -> str:
    if not baseline and edited:
        return "edited_only"
    if baseline and not edited:
        return "baseline_only"
    if baseline == edited:
        return "same"
    return "changed"


def task_specific_scores(task: str, case: Dict[str, Any], result: Dict[str, Any], *, prefix: str) -> Dict[str, Any]:
    if task == "MIS":
        scores = score_mis(case, result)
    elif task == "REP":
        scores = score_rep(case, result)
    elif task == "REV":
        scores = score_rev(case, result)
    else:
        scores = {}
    return {f"{prefix}_{key}": value for key, value in scores.items()}


def score_mis(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    answer = all_answers(result)
    binding = case.get("expected_binding", {}) if isinstance(case.get("expected_binding"), dict) else {}
    item_a = binding.get("item_a", {}) if isinstance(binding.get("item_a"), dict) else {}
    item_b = binding.get("item_b", {}) if isinstance(binding.get("item_b"), dict) else {}
    a_fact = str(item_a.get("expected_fact", "")).strip()
    b_fact = str(item_b.get("expected_fact", "")).strip()
    a_name = str(item_a.get("name", "")).strip()
    b_name = str(item_b.get("name", "")).strip()

    a_fact_present = bool(a_fact and a_fact in answer)
    b_fact_present = bool(b_fact and b_fact in answer)
    binding_complete = a_fact_present and b_fact_present
    possible_swap = False
    if a_fact and b_fact and a_name and b_name:
        possible_swap = near(answer, a_name, b_fact) or near(answer, b_name, a_fact)

    return {
        "a_fact_present": a_fact_present,
        "b_fact_present": b_fact_present,
        "entity_binding_complete": binding_complete,
        "possible_attribute_swap": possible_swap,
        "mis_score": int(binding_complete) - int(possible_swap),
    }


def score_rep(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    answer = all_answers(result)
    false_claim = str(case.get("repeated_false_claim", "")).strip()
    correct_fact = str(case.get("correct_fact", "")).strip()
    wrong_terms = important_terms(false_claim)
    correct_terms = important_terms(correct_fact)
    correction = has_marker(answer, CORRECTION_MARKERS)
    correct_recovered = any(term in answer for term in correct_terms)
    false_repeated = any(term in answer for term in wrong_terms) and not correction
    resistance = correction and correct_recovered and not false_repeated
    return {
        "has_correction": correction,
        "correct_fact_recovered": correct_recovered,
        "false_claim_repeated_without_correction": false_repeated,
        "false_claim_resistance": resistance,
        "rep_score": int(resistance) - int(false_repeated),
    }


def score_rev(case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    answer = all_answers(result)
    injected = str(case.get("injected_false_claim", "")).strip()
    correction_fact = str(case.get("correction_fact", "")).strip()
    wrong_terms = important_terms(injected)
    correct_terms = important_terms(correction_fact)
    correction = has_marker(answer, CORRECTION_MARKERS)
    repair_language = has_marker(answer, ["修复", "修正", "更正", "废弃", "弃用", "不再沿用", "标记"])
    correct_recovered = any(term in answer for term in correct_terms)
    old_error_recurs = any(term in answer for term in wrong_terms) and not correction
    repair_success = correction and correct_recovered and not old_error_recurs
    return {
        "has_correction": correction,
        "has_repair_language": repair_language,
        "correct_fact_recovered": correct_recovered,
        "old_error_recurs_without_correction": old_error_recurs,
        "repair_success": repair_success,
        "rev_score": int(repair_success) + int(repair_language) - int(old_error_recurs),
    }


def delta_scores(row: Dict[str, Any], task: str) -> Dict[str, Any]:
    deltas = {
        "edited_curated_covered": int(row.get("edited_curated_turn_count", 0)) > 0,
        "edited_reduced_write_edges": int(row.get("edited_write_edge_count", 0)) < int(row.get("baseline_write_edge_count", 0)),
        "edited_added_contradiction_edges": int(row.get("edited_contradict_edge_count", 0)) > int(row.get("baseline_contradict_edge_count", 0)),
        "edited_added_repair_edges": int(row.get("edited_repair_edge_count", 0)) > int(row.get("baseline_repair_edge_count", 0)),
    }
    score_key = {"MIS": "mis_score", "REP": "rep_score", "REV": "rev_score"}.get(task)
    if score_key:
        deltas["edited_score_delta"] = int(row.get(f"edited_{score_key}", 0)) - int(row.get(f"baseline_{score_key}", 0))
        deltas["edited_improved"] = deltas["edited_score_delta"] > 0
        deltas["edited_regressed"] = deltas["edited_score_delta"] < 0
    return deltas


def summarize(rows: List[Dict[str, Any]], task: str) -> Dict[str, Any]:
    score_key = {"MIS": "mis_score", "REP": "rep_score", "REV": "rev_score"}[task]
    valid_baseline = [row for row in rows if row["baseline_valid"]]
    valid_edited = [row for row in rows if row["edited_valid"]]
    covered = [row for row in rows if row["edited_curated_covered"]]
    return {
        "task": task,
        "total_cases": len(rows),
        "baseline_valid_cases": len(valid_baseline),
        "edited_valid_cases": len(valid_edited),
        "baseline_error_cases": len(rows) - len(valid_baseline),
        "edited_error_cases": len(rows) - len(valid_edited),
        "edited_curated_covered_cases": len(covered),
        "edited_curated_turn_count": sum(int(row.get("edited_curated_turn_count", 0)) for row in rows),
        "edited_curated_fact_count": sum(int(row.get("edited_curated_fact_count", 0)) for row in rows),
        "baseline_avg_score": avg(row.get(f"baseline_{score_key}", 0) for row in valid_baseline),
        "edited_avg_score": avg(row.get(f"edited_{score_key}", 0) for row in valid_edited),
        "covered_edited_avg_score": avg(row.get(f"edited_{score_key}", 0) for row in covered if row["edited_valid"]),
        "edited_improved_cases": sum(1 for row in rows if row.get("edited_improved")),
        "edited_regressed_cases": sum(1 for row in rows if row.get("edited_regressed")),
        "edited_reduced_write_edges_cases": sum(1 for row in rows if row.get("edited_reduced_write_edges")),
        "edited_added_contradiction_edges_cases": sum(1 for row in rows if row.get("edited_added_contradiction_edges")),
        "edited_added_repair_edges_cases": sum(1 for row in rows if row.get("edited_added_repair_edges")),
        "error_types": {
            "baseline": dict(Counter(short_error(row["baseline_error"]) for row in rows if row["baseline_error"])),
            "edited": dict(Counter(short_error(row["edited_error"]) for row in rows if row["edited_error"])),
        },
    }


def has_marker(text: str, markers: Iterable[str]) -> bool:
    return any(marker in text for marker in markers)


def important_terms(text: str) -> List[str]:
    terms = re.findall(r"《[^》]+》|[\u4e00-\u9fff]{2,}|\d+(?:\.\d+)?", text)
    stop = {"知识库", "摘要", "记载", "其为", "属于", "根据", "正确", "说法", "不能", "依据"}
    return [term.strip("《》") for term in terms if term.strip("《》") not in stop and len(term.strip("《》")) >= 2]


def near(text: str, left: str, right: str, window: int = 80) -> bool:
    if not left or not right:
        return False
    positions = [m.start() for m in re.finditer(re.escape(left), text)]
    for pos in positions:
        segment = text[max(0, pos - window): pos + len(left) + window]
        if right in segment:
            return True
    return False


def avg(values: Iterable[Any]) -> float:
    nums = [float(value) for value in values]
    if not nums:
        return 0.0
    return sum(nums) / len(nums)


def short_error(error: str) -> str:
    if not error:
        return ""
    if "Connection error" in error:
        return "Connection error"
    if "Invalid argument" in error:
        return "Invalid argument"
    if "timed out" in error:
        return "timeout"
    if "FileIOWriter" in error:
        return "faiss_write_error"
    return error[:80]


def write_json(path: str, payload: Dict[str, Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: str, payload: Dict[str, Any]) -> None:
    s = payload["summary"]
    lines = [
        f"# {payload['task']} Baseline vs Edited Comparison",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in s.items():
        if isinstance(value, dict):
            continue
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Error Types", "", "```json", json.dumps(s.get("error_types", {}), ensure_ascii=False, indent=2), "```", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")
