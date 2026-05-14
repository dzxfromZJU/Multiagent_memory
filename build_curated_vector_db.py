import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from vector_db import VectorDatabase


MODEL_PATH = "./models/all-MiniLM-L6-v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a FAISS vector index for approved curated bronze facts."
    )
    parser.add_argument(
        "--curated-kb",
        default="curated_bronze_knowledge_LFQA.sqlite3",
        help="SQLite curated knowledge DB produced by run_memory_curation.py.",
    )
    parser.add_argument(
        "--output-db",
        default="vector_db_curated_LFQA",
        help="Output VectorDatabase directory for curated facts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of approved facts to index. 0 means all.",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Append to the output vector DB instead of rebuilding it from scratch.",
    )
    return parser.parse_args()


def load_approved_facts(path: str, limit: int = 0) -> List[Dict[str, Any]]:
    db_path = Path(path)
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT *
            FROM curated_facts
            WHERE status = 'approved'
            ORDER BY kb_id ASC, field ASC, entity_name ASC, fact_id ASC
        """
        if limit > 0:
            sql += " LIMIT ?"
            rows = conn.execute(sql, (limit,)).fetchall()
        else:
            rows = conn.execute(sql).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def fact_to_text(fact: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Curated bronze fact: {fact.get('entity_name', '')}",
            f"fact_id: {fact.get('fact_id', '')}",
            f"kb_id: {fact.get('kb_id', '')}",
            f"entity_id: {fact.get('entity_id', '')}",
            f"field: {fact.get('field', '')}",
            f"value: {fact.get('value', '')}",
            f"normalized_value: {fact.get('normalized_value', '')}",
            f"confidence: {fact.get('confidence', '')}",
        ]
    )


def main() -> None:
    args = parse_args()
    facts = load_approved_facts(args.curated_kb, args.limit)
    vector_db = VectorDatabase(db_path=args.output_db, model_path=MODEL_PATH)
    if not args.no_clear:
        vector_db.clear()

    seen_fact_ids = set()
    added = 0
    for fact in facts:
        fact_id = str(fact.get("fact_id", "")).strip()
        if not fact_id or fact_id in seen_fact_ids:
            continue
        seen_fact_ids.add(fact_id)
        vector_db.add_memory(
            content=fact_to_text(fact),
            source_type="knowledge_base",
            source_ids=[fact_id, str(fact.get("kb_id", ""))],
            created_by="curated_vector_builder",
            confidence=float(fact.get("confidence") or 0.9),
            contamination_status="clean",
            metadata={"curated_fact": fact},
        )
        added += 1

    vector_db.save()
    vector_db.close()
    print(
        json.dumps(
            {
                "curated_kb": args.curated_kb,
                "output_db": args.output_db,
                "approved_facts": len(facts),
                "indexed_facts": added,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
