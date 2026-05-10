import argparse
import json
from pathlib import Path
from typing import Any, Dict

from bronze.memory_curation import MemoryCurationManager


DEFAULT_METADATA_DBS = {
    "peer": "vector_db_bronze_peer/metadata.sqlite3",
    "sequential": "vector_db_bronze_sequential/metadata.sqlite3",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Curate newly generated bronze memories into a separate trusted "
            "derived knowledge store. The immutable bronze_items.json file is "
            "read only and is never modified."
        )
    )
    parser.add_argument(
        "--architecture",
        choices=sorted(DEFAULT_METADATA_DBS),
        default="peer",
        help="Which bronze memory database to curate when --metadata-db is omitted.",
    )
    parser.add_argument(
        "--metadata-db",
        default=None,
        help="Path to a vector DB metadata.sqlite3 file.",
    )
    parser.add_argument(
        "--base-kb",
        default="bronze_items.json",
        help="Read-only base bronze knowledge file used as trusted evidence.",
    )
    parser.add_argument(
        "--curated-kb",
        default="curated_bronze_knowledge.sqlite3",
        help="SQLite file for the trusted derived knowledge store.",
    )
    parser.add_argument(
        "--report-output",
        default="memory_curation_report.json",
        help="JSON report path for this curation run.",
    )
    parser.add_argument(
        "--review-output",
        default="memory_curation_review_queue.json",
        help="JSON export path for facts requiring human review.",
    )
    parser.add_argument(
        "--facts-output",
        default="curated_bronze_facts.json",
        help="Readable JSON export path for approved curated facts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum candidate memories to process. Use 0 for all candidates.",
    )
    parser.add_argument(
        "--exclude-suspected",
        action="store_true",
        help="Only curate memories marked clean.",
    )
    return parser.parse_args()


def compact_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": summary.get("run_id"),
        "candidate_count": summary.get("candidate_count", 0),
        "atomic_fact_count": summary.get("atomic_fact_count", 0),
        "approved_count": summary.get("approved_count", 0),
        "needs_human_review_count": summary.get("needs_human_review_count", 0),
        "rejected_count": summary.get("rejected_count", 0),
    }


def main() -> None:
    args = parse_args()
    metadata_db = args.metadata_db or DEFAULT_METADATA_DBS[args.architecture]

    manager = MemoryCurationManager(
        metadata_db=metadata_db,
        base_kb_file=args.base_kb,
        curated_kb_path=args.curated_kb,
        architecture=args.architecture,
    )
    try:
        summary = manager.run(
            limit=args.limit,
            include_suspected=not args.exclude_suspected,
            review_output=args.review_output,
        )
        manager.store.export_approved_facts(args.facts_output)
    finally:
        manager.close()

    report_path = Path(args.report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print(json.dumps(compact_summary(summary), ensure_ascii=False, indent=2))
    print(f"Curated KB: {args.curated_kb}")
    print(f"Approved facts: {args.facts_output}")
    print(f"Run report: {args.report_output}")
    print(f"Review queue: {args.review_output}")


if __name__ == "__main__":
    main()
