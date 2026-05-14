import argparse
import json
import re
import sqlite3
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


DEFAULT_EDGE_TYPES = [
    "asks",
    "answers",
    "contains",
    "extracts",
    "retrieves",
    "uses",
    "cited",
    "supports",
    "contradicts",
    "contradicted_by",
    "derived_from",
    "promoted_to",
    "rejected_by",
    "deprecated_by",
    "repairs",
    "contaminates",
    "written_by",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a focused propagation subgraph and export it as Mermaid."
    )
    parser.add_argument("--graph-db", default="propagation_graph.sqlite3")
    parser.add_argument(
        "--metadata-db",
        default="",
        help="Optional metadata.sqlite3 used to enrich Memory node labels.",
    )
    parser.add_argument("--output", default="propagation_subgraph.mmd")
    parser.add_argument("--json-output", default="")
    parser.add_argument(
        "--seed",
        action="append",
        default=[],
        help="Seed node id, for example memory:mem_8bfc092a84d5. Can be repeated.",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Match nodes whose label or payload contains this text. Can be repeated.",
    )
    parser.add_argument(
        "--turn-range",
        action="append",
        default=[],
        help="Include turn ids in an inclusive range, for example peer_000006:peer_000012.",
    )
    parser.add_argument(
        "--edge-type",
        action="append",
        default=[],
        help="Edge type whitelist. Defaults to common provenance/propagation edges.",
    )
    parser.add_argument("--hops", type=int, default=1)
    parser.add_argument("--max-nodes", type=int, default=80)
    parser.add_argument("--max-edges", type=int, default=160)
    parser.add_argument("--direction", choices=["both", "in", "out"], default="both")
    parser.add_argument(
        "--title",
        default="Memory hallucination propagation subgraph",
        help="Mermaid graph title comment.",
    )
    return parser.parse_args()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def load_node(conn: sqlite3.Connection, node_id: str) -> Dict[str, Any]:
    row = conn.execute("SELECT * FROM graph_nodes WHERE node_id = ?", (node_id,)).fetchone()
    return decode_node(row) if row else {}


def seed_nodes(conn: sqlite3.Connection, args: argparse.Namespace) -> Set[str]:
    seeds = set(args.seed)
    for keyword in args.keyword:
        like = f"%{keyword}%"
        rows = conn.execute(
            """
            SELECT node_id FROM graph_nodes
            WHERE label LIKE ? OR payload LIKE ?
            ORDER BY node_type, node_id
            """,
            (like, like),
        ).fetchall()
        seeds.update(row["node_id"] for row in rows)
    for turn_range in args.turn_range:
        seeds.update(turn_nodes_in_range(conn, turn_range))
    return {node_id for node_id in seeds if load_node(conn, node_id)}


def turn_nodes_in_range(conn: sqlite3.Connection, value: str) -> Set[str]:
    if ":" not in value:
        node_id = f"turn:{value}" if not value.startswith("turn:") else value
        return {node_id} if load_node(conn, node_id) else set()
    start, end = value.split(":", 1)
    start = start.removeprefix("turn:")
    end = end.removeprefix("turn:")
    prefix = common_prefix(start, end)
    start_num = trailing_number(start)
    end_num = trailing_number(end)
    if start_num is None or end_num is None:
        return set()
    width = max(len(str(start_num)), len(str(end_num)), len(re.search(r"(\d+)$", start).group(1)))
    nodes = set()
    for number in range(start_num, end_num + 1):
        node_id = f"turn:{prefix}{number:0{width}d}"
        if load_node(conn, node_id):
            nodes.add(node_id)
    return nodes


def extract_subgraph(
    conn: sqlite3.Connection,
    seeds: Set[str],
    edge_types: List[str],
    hops: int,
    direction: str,
    max_nodes: int,
    max_edges: int,
) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []
    edge_ids: Set[str] = set()
    queue = deque((seed, 0) for seed in sorted(seeds))

    for seed in seeds:
        node = load_node(conn, seed)
        if node:
            nodes[seed] = node

    while queue and len(nodes) < max_nodes and len(edges) < max_edges:
        node_id, depth = queue.popleft()
        if depth >= hops:
            continue
        for edge in adjacent_edges(conn, node_id, edge_types, direction):
            if edge["edge_id"] in edge_ids:
                continue
            edge_ids.add(edge["edge_id"])
            edges.append(edge)
            for adjacent in [edge["source_id"], edge["target_id"]]:
                if adjacent not in nodes and len(nodes) < max_nodes:
                    node = load_node(conn, adjacent)
                    if node:
                        nodes[adjacent] = node
                        queue.append((adjacent, depth + 1))
            if len(edges) >= max_edges:
                break
    return nodes, edges


def adjacent_edges(
    conn: sqlite3.Connection, node_id: str, edge_types: List[str], direction: str
) -> List[Dict[str, Any]]:
    clauses = []
    params: List[Any] = []
    if direction in {"both", "out"}:
        clauses.append("source_id = ?")
        params.append(node_id)
    if direction in {"both", "in"}:
        clauses.append("target_id = ?")
        params.append(node_id)
    type_placeholders = ",".join("?" for _ in edge_types)
    params.extend(edge_types)
    rows = conn.execute(
        f"""
        SELECT * FROM graph_edges_unified
        WHERE ({' OR '.join(clauses)})
          AND edge_type IN ({type_placeholders})
        ORDER BY edge_type, source_id, target_id
        """,
        params,
    ).fetchall()
    return [decode_edge(row) for row in rows]


def to_mermaid(nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]], title: str) -> str:
    lines = [
        f"%% {title}",
        "flowchart TD",
    ]
    for node_id, node in sorted(nodes.items()):
        lines.append(f"  {mermaid_id(node_id)}[\"{node_label(node)}\"]")
    for edge in edges:
        if edge["source_id"] not in nodes or edge["target_id"] not in nodes:
            continue
        lines.append(
            f"  {mermaid_id(edge['source_id'])} -- \"{escape_label(edge['edge_type'])}\" --> {mermaid_id(edge['target_id'])}"
        )
    lines.extend(class_defs())
    for node_id, node in sorted(nodes.items()):
        lines.append(f"  class {mermaid_id(node_id)} {class_name(node['node_type'])};")
    return "\n".join(lines) + "\n"


def node_label(node: Dict[str, Any]) -> str:
    node_type = node.get("node_type", "")
    label = node.get("label", "")
    payload = node.get("payload") or {}
    if node_type == "Memory":
        content = payload.get("content") or payload.get("label") or label
        return escape_label(f"Memory\\n{shorten(content, 42)}\\n{node['node_id'].split(':', 1)[-1]}")
    if node_type == "Claim":
        text = payload.get("text") or payload.get("claim") or label
        return escape_label(f"Claim\\n{shorten(text, 48)}")
    if node_type == "Question":
        question = payload.get("question") or label
        return escape_label(f"Question\\n{shorten(question, 48)}")
    if node_type == "Answer":
        answer = payload.get("answer") or payload.get("text") or label
        return escape_label(f"Answer\\n{shorten(answer, 48)}")
    if node_type == "Turn":
        return escape_label(f"Turn\\n{label}")
    if node_type == "KBItem":
        return escape_label(f"KB\\n{label}")
    if node_type == "Agent":
        return escape_label(f"Agent\\n{label}")
    return escape_label(f"{node_type}\\n{shorten(label, 48)}")


def enrich_memory_nodes(nodes: Dict[str, Dict[str, Any]], metadata_db: str) -> None:
    path = Path(metadata_db)
    if not path.exists():
        return
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        for node in nodes.values():
            if node.get("node_type") != "Memory":
                continue
            payload = node.get("payload") or {}
            if payload.get("content"):
                continue
            memory_id = str(node.get("node_id", "")).split(":", 1)[-1]
            row = conn.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
            if not row:
                continue
            memory = dict(row)
            for key in ["source_ids", "derived_from"]:
                memory[key] = decode_json(memory.get(key), [])
            node["payload"] = memory
            node["label"] = memory.get("content") or node.get("label", "")
    finally:
        conn.close()


def class_defs() -> List[str]:
    return [
        "  classDef Turn fill:#f8f9fa,stroke:#495057,color:#212529;",
        "  classDef Question fill:#e7f5ff,stroke:#1c7ed6,color:#102a43;",
        "  classDef Answer fill:#e6fcf5,stroke:#0ca678,color:#063b2f;",
        "  classDef Claim fill:#fff3bf,stroke:#f08c00,color:#3b2500;",
        "  classDef Memory fill:#ffe3e3,stroke:#e03131,color:#3b0a0a;",
        "  classDef KBItem fill:#e5dbff,stroke:#7048e8,color:#24124d;",
        "  classDef EditedKnowledge fill:#d3f9d8,stroke:#2b8a3e,color:#0b2e13;",
        "  classDef Agent fill:#f1f3f5,stroke:#868e96,color:#212529;",
        "  classDef Editor fill:#f1f3f5,stroke:#868e96,color:#212529;",
    ]


def class_name(node_type: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", node_type)


def mermaid_id(node_id: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", node_id)


def escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', "'").replace("\r", " ").replace("\n", "<br/>")


def shorten(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def trailing_number(value: str) -> int | None:
    match = re.search(r"(\d+)$", value)
    return int(match.group(1)) if match else None


def common_prefix(left: str, right: str) -> str:
    left_prefix = re.sub(r"\d+$", "", left)
    right_prefix = re.sub(r"\d+$", "", right)
    return left_prefix if left_prefix == right_prefix else ""


def shorten(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def decode_node(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["payload"] = decode_json(data.get("payload"), {})
    return data


def decode_edge(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["payload"] = decode_json(data.get("payload"), {})
    return data


def decode_json(value: Any, default: Any) -> Any:
    if not isinstance(value, str) or not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def write_json(path: str, nodes: Dict[str, Dict[str, Any]], edges: Iterable[Dict[str, Any]]) -> None:
    payload = {
        "nodes": list(nodes.values()),
        "edges": list(edges),
        "node_count": len(nodes),
        "edge_count": len(list(edges)) if not isinstance(edges, list) else len(edges),
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    graph_db = Path(args.graph_db)
    if not graph_db.exists():
        raise FileNotFoundError(graph_db)
    edge_types = args.edge_type or DEFAULT_EDGE_TYPES
    conn = connect(str(graph_db))
    try:
        seeds = seed_nodes(conn, args)
        if not seeds:
            raise ValueError("No seed nodes matched. Provide --seed, --keyword, or --turn-range.")
        nodes, edges = extract_subgraph(
            conn,
            seeds,
            edge_types,
            args.hops,
            args.direction,
            args.max_nodes,
            args.max_edges,
        )
    finally:
        conn.close()

    if args.metadata_db:
        enrich_memory_nodes(nodes, args.metadata_db)

    Path(args.output).write_text(to_mermaid(nodes, edges, args.title), encoding="utf-8")
    if args.json_output:
        write_json(args.json_output, nodes, edges)
    print(
        json.dumps(
            {
                "output": args.output,
                "json_output": args.json_output,
                "seed_count": len(seeds),
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
