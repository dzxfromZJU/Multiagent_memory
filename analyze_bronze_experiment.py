import argparse

from bronze.bronze_qa_system import ARCHITECTURES, BRONZE_DATA_FILE, MODEL_PATH, PEER, SEQUENTIAL
from bronze.bronze_memory import ArchitectureMemory
from bronze.experiment_metrics import MemoryExperimentAnalyzer
from bronze.memory_auditor import MemoryAuditor
from vector_db import VectorDatabase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build bronze memory experiment report.")
    parser.add_argument(
        "--architecture",
        "-a",
        choices=[SEQUENTIAL, PEER],
        default=SEQUENTIAL,
        help="Memory architecture to analyze.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="bronze_memory_experiment_report.json",
        help="Output report JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ARCHITECTURES[args.architecture]
    vector_db = VectorDatabase(db_path=config["vector_db"], model_path=MODEL_PATH)
    memory = ArchitectureMemory(config["memory"], vector_db=vector_db)
    auditor = MemoryAuditor(memory, data_file=BRONZE_DATA_FILE, vector_db=vector_db)
    analyzer = MemoryExperimentAnalyzer(auditor)
    report = analyzer.save_report(args.output)

    print("Experiment report written:", args.output)
    print("Memory counts:", report["memory_counts"])
    print("Audit summary:", report["audit_summary"])
    print("Metrics:", report["metrics"])


if __name__ == "__main__":
    main()
