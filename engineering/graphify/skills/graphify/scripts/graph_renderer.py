#!/usr/bin/env python3
"""
graph_renderer.py — Render a graph_builder.py knowledge graph to multiple formats.

Formats:
  mermaid  — Mermaid diagram (paste into Claude chat or any Mermaid viewer)
  dot      — GraphViz DOT (compile with: dot -Tsvg graph.dot -o graph.svg)
  json     — Filtered JSON (hub nodes + edges, suitable for piping)
  ascii    — ASCII adjacency list (terminal-friendly)
  summary  — Plain-English insight report (default)

Usage:
  python graph_renderer.py graph.json
  python graph_renderer.py graph.json --format mermaid
  python graph_renderer.py graph.json --format dot > codebase.dot
  python graph_renderer.py graph.json --format summary --top-hubs 10 --orphans
  python graph_renderer.py --sample
  python graph_renderer.py --help
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

MERMAID_TYPE_SHAPE = {
    "file":       "([{label}])",
    "class":      "([{label}])",
    "function":   "({label})",
    "method":     "({label})",
    "interface":  "[/{label}/]",
    "struct":     "([{label}])",
    "module":     "[[{label}]]",
    "external":   "[\"{label}\"]",
    "h1":         ">{label}]",
    "h2":         ">{label}]",
    "config_key": ">>{label}]",
    "import":     "[\"{label}\"]",
    "default":    "[{label}]",
}

RELATION_STYLE = {
    "contains": "-->",
    "imports":  "-.->",
    "calls":    "==>",
    "extends":  "-->|extends|",
    "links_to": "-.-|link|->",
    "defines":  "-->",
    "default":  "-->",
}

# Type → Mermaid node class
MERMAID_CLASS = {
    "file": "file",
    "class": "cls",
    "function": "fn",
    "interface": "iface",
    "external": "ext",
    "h1": "doc",
    "h2": "doc",
    "config_key": "cfg",
}


def safe_mermaid_id(id_: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", id_)[:60] if id_ else "_"


def mermaid_shape(node: dict) -> str:
    type_ = node.get("type", "default")
    label = node.get("label", node.get("id", "?"))[:40].replace('"', "'")
    template = MERMAID_TYPE_SHAPE.get(type_, MERMAID_TYPE_SHAPE["default"])
    return template.replace("{label}", label)


def render_mermaid(graph: dict, max_nodes: int = 60, filter_type: Optional[str] = None) -> str:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Sort by degree, pick top N
    nodes_sorted = sorted(nodes, key=lambda n: n.get("degree", 0), reverse=True)
    if filter_type:
        nodes_sorted = [n for n in nodes_sorted if n.get("type") == filter_type]
    shown_nodes = nodes_sorted[:max_nodes]
    shown_ids = {n["id"] for n in shown_nodes}

    lines = ["graph TD"]
    lines.append('  classDef file fill:#e8f4f8,stroke:#2196F3')
    lines.append('  classDef cls fill:#e8f5e9,stroke:#4CAF50')
    lines.append('  classDef fn fill:#fff3e0,stroke:#FF9800')
    lines.append('  classDef iface fill:#f3e5f5,stroke:#9C27B0')
    lines.append('  classDef ext fill:#fafafa,stroke:#9E9E9E,stroke-dasharray:5')
    lines.append('  classDef doc fill:#fff9c4,stroke:#FFC107')
    lines.append('  classDef cfg fill:#fce4ec,stroke:#E91E63')

    node_id_map: Dict[str, str] = {}
    for node in shown_nodes:
        mid = safe_mermaid_id(node["id"])
        node_id_map[node["id"]] = mid
        shape = mermaid_shape(node)
        lines.append(f"  {mid}{shape}")
        cls = MERMAID_CLASS.get(node.get("type", ""), "")
        if cls:
            lines.append(f"  class {mid} {cls}")

    shown_edges = 0
    for edge in edges:
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src in shown_ids and tgt in shown_ids:
            msrc = node_id_map.get(src, safe_mermaid_id(src))
            mtgt = node_id_map.get(tgt, safe_mermaid_id(tgt))
            rel = RELATION_STYLE.get(edge.get("relation", "default"), RELATION_STYLE["default"])
            lines.append(f"  {msrc} {rel} {mtgt}")
            shown_edges += 1
            if shown_edges >= 200:
                lines.append("  %% (edge limit reached — use --max-nodes to expand)")
                break

    return "\n".join(lines)


def render_dot(graph: dict, max_nodes: int = 200, filter_type: Optional[str] = None) -> str:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    nodes_sorted = sorted(nodes, key=lambda n: n.get("degree", 0), reverse=True)
    if filter_type:
        nodes_sorted = [n for n in nodes_sorted if n.get("type") == filter_type]
    shown_nodes = nodes_sorted[:max_nodes]
    shown_ids = {n["id"] for n in shown_nodes}

    DOT_COLOR = {
        "file": "#E3F2FD", "class": "#E8F5E9", "function": "#FFF3E0",
        "interface": "#F3E5F5", "external": "#FAFAFA", "h1": "#FFFDE7",
    }

    lines = ['digraph knowledge_graph {', '  rankdir=LR;', '  node [fontname="Helvetica", fontsize=10];']
    for node in shown_nodes:
        nid = safe_dot_id(node["id"])
        label = node.get("label", "?")[:40].replace('"', '\\"')
        color = DOT_COLOR.get(node.get("type", ""), "#FFFFFF")
        shape = "box" if node.get("type") == "file" else "ellipse"
        lines.append(f'  {nid} [label="{label}", shape={shape}, style=filled, fillcolor="{color}"];')

    shown_edges = 0
    for edge in edges:
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src in shown_ids and tgt in shown_ids:
            msrc = safe_dot_id(src)
            mtgt = safe_dot_id(tgt)
            rel = edge.get("relation", "")
            style = "dashed" if rel == "imports" else "solid"
            lines.append(f'  {msrc} -> {mtgt} [label="{rel}", style={style}];')
            shown_edges += 1
            if shown_edges >= 500:
                break

    lines.append("}")
    return "\n".join(lines)


def safe_dot_id(id_: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", id_)[:80]
    return f"n_{clean}" if clean and clean[0].isdigit() else clean or "n_unknown"


def render_ascii(graph: dict, max_nodes: int = 30, filter_type: Optional[str] = None) -> str:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    nodes_sorted = sorted(nodes, key=lambda n: n.get("degree", 0), reverse=True)
    if filter_type:
        nodes_sorted = [n for n in nodes_sorted if n.get("type") == filter_type]
    top_nodes = nodes_sorted[:max_nodes]
    shown_ids = {n["id"] for n in top_nodes}

    adjacency: Dict[str, List[str]] = {n["id"]: [] for n in top_nodes}
    for edge in edges:
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src in shown_ids and tgt in shown_ids:
            adjacency[src].append(f"{edge.get('relation', '?')} → {_short_label(tgt, nodes)}")

    lines = [f"KNOWLEDGE GRAPH — top {len(top_nodes)} nodes by degree", "=" * 60]
    for node in top_nodes:
        label = node.get("label", node["id"])[:40]
        type_ = node.get("type", "?")
        degree = node.get("degree", 0)
        lines.append(f"\n  [{type_:12s}] {label}  (degree={degree})")
        for conn in adjacency.get(node["id"], [])[:5]:
            lines.append(f"    ├── {conn}")
    return "\n".join(lines)


def _short_label(node_id: str, nodes: list) -> str:
    for n in nodes:
        if n["id"] == node_id:
            return n.get("label", node_id)[:30]
    return node_id.split(":")[-1][:30]


def render_summary(
    graph: dict,
    top_hubs: int = 5,
    show_orphans: bool = False,
) -> str:
    stats = graph.get("stats", {})
    hubs = graph.get("hub_nodes", [])[:top_hubs]
    orphans = graph.get("orphan_nodes", [])
    patterns = graph.get("patterns", [])
    clusters = graph.get("clusters", [])

    lines = [
        "GRAPHIFY — KNOWLEDGE GRAPH SUMMARY",
        "=" * 60,
        f"Nodes    : {stats.get('node_count', 0)}",
        f"Edges    : {stats.get('edge_count', 0)}",
        f"Clusters : {stats.get('cluster_count', 0)}  (connected components)",
        f"Hubs     : {stats.get('hub_count', 0)}  (degree > 2)",
        f"Orphans  : {stats.get('orphan_count', 0)}  (degree = 0)",
        "",
        "ARCHITECTURAL PATTERNS",
        "-" * 40,
    ]
    for p in patterns:
        lines.append(f"  • {p}")

    lines += ["", f"TOP {top_hubs} HUB NODES (highest degree = widest blast radius)", "-" * 40]
    for n in hubs:
        label = n.get("label", "?")[:40]
        type_ = n.get("type", "?")
        degree = n.get("degree", 0)
        file_ = Path(n.get("file", "")).name
        lines.append(f"  [{type_:12s}] {label:40s}  degree={degree}  ({file_})")

    if clusters:
        lines += ["", "LARGEST CLUSTERS (top 5)", "-" * 40]
        for i, cluster in enumerate(clusters[:5], 1):
            size = len(cluster)
            preview = ", ".join(_short_label(nid, graph.get("nodes", [])) for nid in cluster[:3])
            lines.append(f"  Cluster {i}: {size} nodes  [{preview}{'...' if size > 3 else ''}]")

    if show_orphans and orphans:
        lines += ["", f"ORPHAN NODES ({len(orphans)} shown, degree=0)", "-" * 40]
        for n in orphans[:20]:
            label = n.get("label", "?")[:40]
            type_ = n.get("type", "?")
            file_ = Path(n.get("file", "")).name
            lines.append(f"  [{type_:12s}] {label:40s}  ({file_})")

    lines += [
        "",
        "NEXT STEPS",
        "-" * 40,
        "  1. Ask Claude: 'What does this graph suggest about the architecture?'",
        "  2. Focus on hub nodes — they carry the highest change risk.",
        "  3. Review orphans — possible dead code or missing wiring.",
        "  4. Re-run with --format mermaid and paste into Claude chat for visual.",
    ]
    return "\n".join(lines)


import re  # noqa: E402  (needed by safe_mermaid_id / safe_dot_id above)


SAMPLE_GRAPH = {
    "nodes": [
        {"id": "file:src/services/user_service.py", "label": "user_service.py", "type": "file", "file": "src/services/user_service.py", "degree": 4},
        {"id": "class:src/services/user_service.py:UserService", "label": "UserService", "type": "class", "file": "src/services/user_service.py", "degree": 2},
        {"id": "function:src/services/user_service.py:get_user", "label": "get_user", "type": "function", "file": "src/services/user_service.py", "degree": 1},
        {"id": "file:src/repositories/user_repo.py", "label": "user_repo.py", "type": "file", "file": "src/repositories/user_repo.py", "degree": 2},
        {"id": "class:src/repositories/user_repo.py:UserRepository", "label": "UserRepository", "type": "class", "file": "src/repositories/user_repo.py", "degree": 1},
        {"id": "module:sqlalchemy", "label": "sqlalchemy", "type": "external", "file": "", "degree": 1},
    ],
    "edges": [
        {"source": "file:src/services/user_service.py", "target": "class:src/services/user_service.py:UserService", "relation": "contains", "file": "src/services/user_service.py", "line": 1},
        {"source": "file:src/services/user_service.py", "target": "file:src/repositories/user_repo.py", "relation": "imports", "file": "src/services/user_service.py", "line": 2},
        {"source": "file:src/repositories/user_repo.py", "target": "module:sqlalchemy", "relation": "imports", "file": "src/repositories/user_repo.py", "line": 1},
    ],
    "stats": {"node_count": 6, "edge_count": 3, "cluster_count": 1, "hub_count": 1, "orphan_count": 0},
    "hub_nodes": [{"id": "file:src/services/user_service.py", "label": "user_service.py", "type": "file", "file": "src/services/user_service.py", "degree": 4}],
    "orphan_nodes": [],
    "clusters": [["file:src/services/user_service.py", "file:src/repositories/user_repo.py"]],
    "patterns": ["Layered architecture (Repository/Service/Entity) signals detected"],
}


def run_sample(fmt: str) -> None:
    graph = SAMPLE_GRAPH
    if fmt == "mermaid":
        print(render_mermaid(graph))
    elif fmt == "dot":
        print(render_dot(graph))
    elif fmt == "ascii":
        print(render_ascii(graph))
    elif fmt == "json":
        print(json.dumps({"hub_nodes": graph["hub_nodes"], "stats": graph["stats"]}, indent=2))
    else:
        print(render_summary(graph, top_hubs=3, show_orphans=True))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a knowledge graph from graph_builder.py to multiple output formats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("graph_json", nargs="?", help="JSON output from graph_builder.py")
    parser.add_argument("--format", choices=["mermaid", "dot", "ascii", "json", "summary"], default="summary")
    parser.add_argument("--max-nodes", type=int, default=60, help="Max nodes to render (default 60)")
    parser.add_argument("--filter-type", help="Only show nodes of this type (e.g. class, function, file)")
    parser.add_argument("--top-hubs", type=int, default=5, help="Number of hub nodes in summary (default 5)")
    parser.add_argument("--orphans", action="store_true", help="Show orphan nodes in summary")
    parser.add_argument("--sample", action="store_true", help="Render built-in sample graph and exit")

    args = parser.parse_args()

    if args.sample:
        run_sample(args.format)
        return

    if not args.graph_json:
        parser.print_help()
        sys.exit(1)

    graph_path = Path(args.graph_json)
    if not graph_path.exists():
        print(f"ERROR: graph file not found: {graph_path}", file=sys.stderr)
        sys.exit(1)

    with open(graph_path, encoding="utf-8") as f:
        graph = json.load(f)

    if args.format == "mermaid":
        print(render_mermaid(graph, args.max_nodes, args.filter_type))
    elif args.format == "dot":
        print(render_dot(graph, args.max_nodes, args.filter_type))
    elif args.format == "ascii":
        print(render_ascii(graph, args.max_nodes, args.filter_type))
    elif args.format == "json":
        output = {
            "stats": graph.get("stats", {}),
            "hub_nodes": graph.get("hub_nodes", [])[:args.top_hubs],
            "patterns": graph.get("patterns", []),
        }
        print(json.dumps(output, indent=2))
    else:
        print(render_summary(graph, args.top_hubs, args.orphans))


if __name__ == "__main__":
    main()
