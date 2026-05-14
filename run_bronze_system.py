import argparse

from bronze.bronze_qa_system import (
    ARCHITECTURES,
    CURATED_HYBRID,
    CURATED_LIGHT,
    CURATED_VECTOR,
    PEER,
    SEQUENTIAL,
    answer_question,
    initialize_bronze_system,
    safe_print,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动青铜器多智能体问答系统")
    parser.add_argument(
        "--architecture",
        "-a",
        choices=[SEQUENTIAL, PEER],
        default=SEQUENTIAL,
        help="选择多智能体架构: sequential=分析问题-回答-校对, peer=对等协同",
    )
    parser.add_argument(
        "--rebuild-vector-db",
        action="store_true",
        help="Rebuild the FAISS index and SQLite metadata from bronze_items.json before starting.",
    )
    parser.add_argument(
        "--curated-kb",
        default="",
        help="Optional read-only curated knowledge SQLite DB for edited/enhanced runs.",
    )
    parser.add_argument(
        "--curated-mode",
        choices=[CURATED_LIGHT, CURATED_VECTOR, CURATED_HYBRID],
        default=CURATED_LIGHT,
        help="How to retrieve curated knowledge: light, vector, or hybrid.",
    )
    parser.add_argument(
        "--curated-vector-db",
        default="",
        help="Optional VectorDatabase directory built from curated facts for vector/hybrid modes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    architecture = args.architecture
    config = ARCHITECTURES[architecture]

    safe_print("=== 青铜器多智能体问答系统 ===")
    safe_print(f"当前架构: {config['label']}")
    safe_print(f"记忆文件: {config['memory']}")
    safe_print(f"向量库目录: {config['vector_db']}")

    vector_db, memory = initialize_bronze_system(
        architecture,
        rebuild_vector_db=args.rebuild_vector_db,
    )

    safe_print("\n可以询问青铜器名称、器类、年代、出土地、形制、纹饰、收藏地等问题。")
    safe_print("输入 exit、quit 或 退出 结束对话。")

    while True:
        try:
            question = input("\n用户：").strip()
        except (EOFError, KeyboardInterrupt):
            safe_print("\n已结束。")
            break

        if question.lower() in {"exit", "quit"} or question == "退出":
            safe_print("已结束。")
            break
        if not question:
            continue

        safe_print("\n=== 智能体协作中 ===")
        try:
            final_answer, audit_text = answer_question(
                architecture,
                question,
                vector_db,
                memory,
                curated_kb_path=args.curated_kb or None,
                curated_mode=args.curated_mode,
                curated_vector_db_path=args.curated_vector_db,
            )
        except Exception as exc:
            safe_print(f"处理失败: {exc}")
            continue

        safe_print("\n=== 最终回答 ===")
        safe_print(final_answer or "未能生成回答。")

        if audit_text:
            title = "校对结果" if architecture == SEQUENTIAL else "协同过程摘要"
            safe_print(f"\n=== {title} ===")
            safe_print(audit_text)


if __name__ == "__main__":
    main()
