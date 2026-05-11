import argparse
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
    "应为",
    "实际",
    "知识库记载",
    "根据知识库",
    "而不是",
    "矛盾",
    "冲突",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare baseline and curated-KB edited FPI test results."
    )
    parser.add_argument("--cases", default="tests_peer_FPI_cases.json")
    parser.add_argument("--baseline", default="results_peer_FPI.json")
    parser.add_argument("--edited", default="results_peer_FPI_edited.json")
    parser.add_argument("--json-output", default="compare_fpi_baseline_edited.json")
    parser.add_argument("--csv-output", default="compare_fpi_baseline_edited.csv")
    parser.add_argument("--markdown-output", default="compare_fpi_baseline_edited.md")
    return parser.parse_args()


def load_json(path: str) -> Dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def result_by_id(path: str) -> Dict[str, Dict[str, Any]]:
    data = load_json(path)
    return {
        str(item.get("test_id")): item
        for item in data.get("results", [])
        if isinstance(item, dict) and item.get("test_id")
    }


def cases_by_id(path: str) -> Dict[str, Dict[str, Any]]:
    data = load_json(path)
    return {
        str(item.get("test_id")): item
        for item in data.get("cases", [])
        if isinstance(item, dict) and item.get("test_id")
    }


def final_answer(result: Dict[str, Any]) -> str:
    return str(result.get("final_answer") or "").strip()


def valid_result(result: Dict[str, Any]) -> bool:
    return bool(result) and not result.get("error") and bool(result.get("turns"))


def wrong_value(false_premise: str) -> str:
    if "属于" in false_premise:
        return false_premise.split("属于", 1)[1].split("。", 1)[0].strip()
    if "是" in false_premise:
        return false_premise.split("是", 1)[1].split("。", 1)[0].strip()
    return ""


def correct_terms(correct_fact: str, target_name: str) -> List[str]:
    terms = []
    if target_name:
        terms.append(target_name)
    cleaned = correct_fact
    for token in ("知识库记载", "为", "。", "，", "；", "、", "（", "）", "(", ")"):
        cleaned = cleaned.replace(token, "|")
    for part in cleaned.split("|"):
        part = re.sub(r"ID\s*\d+", "", part).strip()
        part = part.strip("《》")
        if len(part) >= 2 and part not in terms:
            terms.append(part)
    return terms


def has_correction(answer: str) -> bool:
    return any(marker in answer for marker in CORRECTION_MARKERS)


def has_correct_fact(answer: str, terms: Iterable[str]) -> bool:
    useful_terms = [term for term in terms if len(term) >= 2]
    if not useful_terms:
        return False
    return any(term in answer for term in useful_terms)


def possible_false_acceptance(answer: str, wrong: str) -> bool:
    if not wrong:
        return False
    if wrong not in answer:
        return False
    return not has_correction(answer)


def turn_logs(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item for item in result.get("turn_logs", []) if isinstance(item, dict)]


def curated_fact_count(result: Dict[str, Any]) -> int:
    return sum(
        len(log.get("curated_knowledge", {}).get("curated_facts", []))
        for log in turn_logs(result)
    )


def used_memory_count(result: Dict[str, Any]) -> int:
    return len(result.get("used_memory_ids", []) or [])


def retrieved_memory_count(result: Dict[str, Any]) -> int:
    return len(result.get("retrieved_memory_ids", []) or [])


def answer_delta(baseline: str, edited: str) -> str:
    if not baseline and edited:
        return "edited_only"
    if baseline and not edited:
        return "baseline_only"
    if baseline == edited:
        return "same"
    return "changed"


def score_result(result: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
    answer = final_answer(result)
    false_premise = str(case.get("false_premise", ""))
    wrong = wrong_value(false_premise)
    terms = correct_terms(
        str(case.get("correct_fact", "")),
        str(case.get("target_item_name", "")),
    )
    return {
        "valid": valid_result(result),
        "error": str(result.get("error", "")),
        "answer_length": len(answer),
        "has_correction": has_correction(answer),
        "has_correct_fact": has_correct_fact(answer, terms),
        "mentions_wrong_value": bool(wrong and wrong in answer),
        "possible_false_acceptance": possible_false_acceptance(answer, wrong),
        "retrieved_memory_count": retrieved_memory_count(result),
        "used_memory_count": used_memory_count(result),
        "curated_fact_count": curated_fact_count(result),
        "curated_covered": curated_fact_count(result) > 0,
    }


def rate(rows: List[Dict[str, Any]], key: str, *, valid_only: bool = True) -> float:
    selected = [row for row in rows if (row.get("valid") or not valid_only)]
    if not selected:
        return 0.0
    return sum(1 for row in selected if row.get(key)) / len(selected)


def summarize_side(rows: List[Dict[str, Any]], prefix: str) -> Dict[str, Any]:
    side_rows = [
        {
            "valid": row[f"{prefix}_valid"],
            "has_correction": row[f"{prefix}_has_correction"],
            "has_correct_fact": row[f"{prefix}_has_correct_fact"],
            "possible_false_acceptance": row[f"{prefix}_possible_false_acceptance"],
            "curated_covered": row[f"{prefix}_curated_covered"],
            "curated_fact_count": row[f"{prefix}_curated_fact_count"],
        }
        for row in rows
    ]
    valid_rows = [row for row in side_rows if row["valid"]]
    return {
        "total_cases": len(side_rows),
        "valid_cases": len(valid_rows),
        "error_cases": len(side_rows) - len(valid_rows),
        "correction_rate": rate(side_rows, "has_correction"),
        "correct_fact_rate": rate(side_rows, "has_correct_fact"),
        "possible_false_acceptance_rate": rate(side_rows, "possible_false_acceptance"),
        "curated_covered_cases": sum(1 for row in side_rows if row["curated_covered"]),
        "curated_fact_count": sum(int(row["curated_fact_count"]) for row in side_rows),
    }


def compare(args: argparse.Namespace) -> Dict[str, Any]:
    cases = cases_by_id(args.cases)
    baseline = result_by_id(args.baseline)
    edited = result_by_id(args.edited)
    all_ids = sorted(set(cases) | set(baseline) | set(edited))

    rows = []
    for test_id in all_ids:
        case = cases.get(test_id, {})
        base_result = baseline.get(test_id, {})
        edit_result = edited.get(test_id, {})
        base_score = score_result(base_result, case)
        edit_score = score_result(edit_result, case)
        row = {
            "test_id": test_id,
            "false_premise_type": case.get("false_premise_type", ""),
            "target_item_id": ",".join(str(x) for x in case.get("target_item_ids", [])),
            "false_premise": case.get("false_premise", ""),
            "correct_fact": case.get("correct_fact", ""),
            "answer_delta": answer_delta(final_answer(base_result), final_answer(edit_result)),
        }
        for key, value in base_score.items():
            row[f"baseline_{key}"] = value
        for key, value in edit_score.items():
            row[f"edited_{key}"] = value
        row["edited_added_correction"] = (
            not row["baseline_has_correction"] and row["edited_has_correction"]
        )
        row["edited_lost_correction"] = (
            row["baseline_has_correction"] and not row["edited_has_correction"]
        )
        row["edited_added_correct_fact"] = (
            not row["baseline_has_correct_fact"] and row["edited_has_correct_fact"]
        )
        row["edited_lost_correct_fact"] = (
            row["baseline_has_correct_fact"] and not row["edited_has_correct_fact"]
        )
        rows.append(row)

    covered_rows = [row for row in rows if row["edited_curated_covered"]]
    summary = {
        "baseline": summarize_side(rows, "baseline"),
        "edited": summarize_side(rows, "edited"),
        "edited_curated_covered_subset": summarize_side(covered_rows, "edited")
        if covered_rows
        else {},
        "comparison": {
            "changed_answers": sum(1 for row in rows if row["answer_delta"] == "changed"),
            "edited_added_correction": sum(1 for row in rows if row["edited_added_correction"]),
            "edited_lost_correction": sum(1 for row in rows if row["edited_lost_correction"]),
            "edited_added_correct_fact": sum(1 for row in rows if row["edited_added_correct_fact"]),
            "edited_lost_correct_fact": sum(1 for row in rows if row["edited_lost_correct_fact"]),
        },
        "false_premise_types": Counter(
            str(row.get("false_premise_type", "")) for row in rows
        ),
    }
    summary["false_premise_types"] = dict(summary["false_premise_types"])
    return {"summary": summary, "rows": rows}


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


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_markdown(path: str, payload: Dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# FPI Baseline vs Edited Comparison",
        "",
        "## Overall",
        "",
        "| Metric | Baseline | Edited |",
        "|---|---:|---:|",
    ]
    for label, key in [
        ("Valid cases", "valid_cases"),
        ("Error cases", "error_cases"),
        ("Correction rate", "correction_rate"),
        ("Correct fact rate", "correct_fact_rate"),
        ("Possible false acceptance rate", "possible_false_acceptance_rate"),
        ("Curated covered cases", "curated_covered_cases"),
        ("Curated fact count", "curated_fact_count"),
    ]:
        base = summary["baseline"].get(key, 0)
        edit = summary["edited"].get(key, 0)
        if key.endswith("_rate"):
            base = pct(float(base))
            edit = pct(float(edit))
        lines.append(f"| {label} | {base} | {edit} |")

    lines.extend(
        [
            "",
            "## Edited Curated-Covered Subset",
            "",
            json.dumps(
                summary.get("edited_curated_covered_subset", {}),
                ensure_ascii=False,
                indent=2,
            ),
            "",
            "## Changes",
            "",
            json.dumps(summary.get("comparison", {}), ensure_ascii=False, indent=2),
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = compare(args)
    write_json(args.json_output, payload)
    write_csv(args.csv_output, payload["rows"])
    write_markdown(args.markdown_output, payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {args.json_output}")
    print(f"CSV: {args.csv_output}")
    print(f"Markdown: {args.markdown_output}")


if __name__ == "__main__":
    main()
