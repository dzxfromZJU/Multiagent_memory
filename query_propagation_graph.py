import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect the propagation graph.")
    parser.add_argument("--graph-db", default="propagation_graph.sqlite3")
    parser.add_argument(
        "--mode",
        choices=["summary", "contamination", "repairs", "node"],
        default="summary",
    )
    parser.add_argument("--node-id", default="", help="Node id for --mode node.")
    parser.add_argument("--limit", type=int, default=20)
    return parser.parse_args()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    return {
        "nodes": {
            row["node_type"]: int(row["count"])
            for row in conn.execute(
                "SELECT node_type, COUNT(*) AS count FROM graph_nodes GROUP BY node_type"
            )
        },
        "edges": {
            row["edge_type"]: int(row["count"])
            for row in conn.execute(
                "SELECT edge_type, COUNT(*) AS count FROM graph_edges_unified GROUP BY edge_type"
            )
        },
    }


def edge_rows(conn: sqlite3.Connection, edge_type: str, limit: int) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT edge_type, source_id, source_type, target_id, target_type, confidence, payload
        FROM graph_edges_unified
        WHERE edge_type = ?
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (edge_type, limit),
    ).fetchall()
    return [decode_row(row) for row in rows]


def node_neighborhood(conn: sqlite3.Connection, node_id: str, limit: int) -> Dict[str, Any]:
    node = conn.execute("SELECT * FROM graph_nodes WHERE node_id = ?", (node_id,)).fetchone()
    outgoing = conn.execute(
        """
        SELECT edge_type, source_id, source_type, target_id, target_type, confidence, payload
        FROM graph_edges_unified
        WHERE source_id = ?
        LIMIT ?
        """,
        (node_id, limit),
    ).fetchall()
    incoming = conn.execute(
        """
        SELECT edge_type, source_id, source_type, target_id, target_type, confidence, payload
        FROM graph_edges_unified
        WHERE target_id = ?
        LIMIT ?
        """,
        (node_id, limit),
    ).fetchall()
    return {
        "node": decode_node(node) if node else None,
        "outgoing": [decode_row(row) for row in outgoing],
        "incoming": [decode_row(row) for row in incoming],
    }


def decode_node(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["payload"] = decode_json(data.get("payload"))
    return data


def decode_row(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["payload"] = decode_json(data.get("payload"))
    return data


def decode_json(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def main() -> None:
    args = parse_args()
    if not Path(args.graph_db).exists():
        raise FileNotFoundError(args.graph_db)
    conn = connect(args.graph_db)
    try:
        if args.mode == "summary":
            payload = summary(conn)
        elif args.mode == "contamination":
            payload = {"contaminates": edge_rows(conn, "contaminates", args.limit)}
        elif args.mode == "repairs":
            payload = {
                "repairs": edge_rows(conn, "repairs", args.limit),
                "deprecated_by": edge_rows(conn, "deprecated_by", args.limit),
            }
        else:
            if not args.node_id:
                raise ValueError("--node-id is required for --mode node")
            payload = node_neighborhood(conn, args.node_id, args.limit)
    finally:
        conn.close()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
