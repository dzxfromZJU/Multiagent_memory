import argparse
import json
from pathlib import Path

from bronze.propagation_graph import PropagationGraphBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a unified Memory Hallucination Propagation Graph."
    )
    parser.add_argument(
        "--results",
        nargs="+",
        default=[
            "results_peer_FPI.json",
            "results_peer_FPI_edited.json",
            "results_peer_MIS.json",
            "results_peer_MIS_edited.json",
            "results_peer_REP.json",
            "results_peer_REP_edited.json",
            "results_peer_REV.json",
            "results_peer_REV_edited.json",
        ],
        help="Result JSON files produced by run_bronze_dialogue_tests.py.",
    )
    parser.add_argument(
        "--metadata-db",
        default="vector_db_bronze_peer/metadata.sqlite3",
        help="Memory Manager SQLite metadata database.",
    )
    parser.add_argument(
        "--curated-db",
        default="curated_bronze_knowledge_LFQA.sqlite3",
        help="Optional curated knowledge SQLite database.",
    )
    parser.add_argument(
        "--curation-report",
        default="memory_curation_LFQA_report.json",
        help="Optional memory curation report JSON.",
    )
    parser.add_argument(
        "--graph-db",
        default="propagation_graph.sqlite3",
        help="Output SQLite graph database.",
    )
    parser.add_argument(
        "--summary-output",
        default="propagation_graph_summary.json",
        help="Output graph summary JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_files = [path for path in args.results if Path(path).exists()]
    missing = [path for path in args.results if not Path(path).exists()]
    if missing:
        print("Skipping missing result files:")
        for path in missing:
            print(f"  {path}")

    builder = PropagationGraphBuilder(
        graph_db=args.graph_db,
        metadata_db=args.metadata_db,
        curated_db=args.curated_db if Path(args.curated_db).exists() else "",
        curation_report=args.curation_report if Path(args.curation_report).exists() else "",
    )
    try:
        summary = builder.build_from_results(result_files)
    finally:
        builder.close()

    with Path(args.summary_output).open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Graph DB: {args.graph_db}")
    print(f"Summary: {args.summary_output}")


if __name__ == "__main__":
    main()
