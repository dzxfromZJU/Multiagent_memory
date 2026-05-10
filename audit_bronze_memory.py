import argparse

from bronze.bronze_qa_system import ARCHITECTURES, BRONZE_DATA_FILE, MODEL_PATH, PEER, SEQUENTIAL
from bronze.bronze_memory import ArchitectureMemory
from bronze.memory_auditor import MemoryAuditor
from vector_db import VectorDatabase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit and edit bronze shared memory.")
    parser.add_argument(
        "--architecture",
        "-a",
        choices=[SEQUENTIAL, PEER],
        default=SEQUENTIAL,
        help="Memory architecture to audit.",
    )
    parser.add_argument(
        "--review-file",
        default="memory_review_items.json",
        help="JSON file for suspected errors that need human review.",
    )
    parser.add_argument(
        "--no-auto-correct",
        action="store_true",
        help="Only detect and export review items; do not auto-correct high-confidence errors.",
    )
    parser.add_argument(
        "--apply-human-review",
        action="store_true",
        help="Apply labels and corrections from --review-file.",
    )
    parser.add_argument(
        "--no-rebuild-vector-db",
        action="store_true",
        help="Do not rebuild the vector DB after editing memory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ARCHITECTURES[args.architecture]
    vector_db = VectorDatabase(db_path=config["vector_db"], model_path=MODEL_PATH)
    memory = ArchitectureMemory(config["memory"], vector_db=vector_db)
    auditor = MemoryAuditor(memory, data_file=BRONZE_DATA_FILE, vector_db=vector_db)

    if args.apply_human_review:
        counts = auditor.apply_human_review(
            args.review_file,
            rebuild_vector_db=not args.no_rebuild_vector_db,
        )
        print("Human review applied:")
        for key, value in counts.items():
            print(f"  {key}: {value}")
        return

    results = auditor.audit(
        auto_correct=not args.no_auto_correct,
        review_file=args.review_file,
        rebuild_vector_db=not args.no_rebuild_vector_db,
    )
    summary = {}
    for result in results:
        summary[result.verdict] = summary.get(result.verdict, 0) + 1

    print("Memory audit finished:")
    for key in sorted(summary):
        print(f"  {key}: {summary[key]}")
    print(f"Human review JSON: {args.review_file}")


if __name__ == "__main__":
    main()
