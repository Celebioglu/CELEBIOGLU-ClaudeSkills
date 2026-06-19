#!/usr/bin/env python3
"""
graph_builder.py — Build a unified knowledge graph from ast_extractor output
and additional file-type parsers (Markdown, YAML, TOML, plain text).

Detects: hub nodes (high degree), orphan nodes (degree 0), clusters
(connected components), and common architectural patterns.

Usage:
  python graph_builder.py entities.json              # from ast_extractor output
  python graph_builder.py entities.json --scan ./src # also parse non-code files
  python graph_builder.py --sample
  python graph_builder.py --help
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Graph data model
# ---------------------------------------------------------------------------

def make_node(id_: str, label: str, type_: str, file_: str = "", line: int = 0) -> dict:
    return {"id": id_, "label": label, "type": type_, "file": file_, "line": line, "degree": 0}


def make_edge(source: str, target: str, relation: str, file_: str = "", line: int = 0) -> dict:
    return {"source": source, "target": target, "relation": relation, "file": file_, "line": line}


# ---------------------------------------------------------------------------
# Load ast_extractor output
# ---------------------------------------------------------------------------

def load_extractor_output(path: Path) -> List[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"Unexpected JSON shape in {path}")


def entities_to_graph(file_results: List[dict]) -> Tuple[Dict[str, dict], List[dict]]:
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []

    for file_result in file_results:
        if file_result.get("skipped"):
            continue
        file_path = file_result.get("file", "")
        lang = file_result.get("lang", "")

        # Add a node for the file itself
        file_id = f"file:{file_path}"
        if file_id not in nodes:
            nodes[file_id] = make_node(file_id, Path(file_path).name, "file", file_path)

        for node in file_result.get("nodes", []):
            name = node["name"]
            type_ = node["type"]
            nid = f"{type_}:{file_path}:{name}"
            if nid not in nodes:
                nodes[nid] = make_node(nid, name, type_, file_path, node.get("line", 0))
            # File → contains → entity
            edges.append(make_edge(file_id, nid, "contains", file_path, node.get("line", 0)))

        for edge in file_result.get("edges", []):
            from_ = edge.get("from", file_path)
            to_ = edge.get("to", "")
            relation = edge.get("relation", "imports")
            line = edge.get("line", 0)

            from_id = f"file:{from_}"
            # Try to resolve the target to a known file node
            to_id = resolve_target(to_, nodes, from_)
            if to_id not in nodes:
                nodes[to_id] = make_node(to_id, to_, "external", "", 0)
            edges.append(make_edge(from_id, to_id, relation, from_, line))

    return nodes, edges


def resolve_target(target: str, nodes: Dict[str, dict], from_file: str) -> str:
    """Try to resolve an import target to a known file node id."""
    # Direct match as file node
    direct = f"file:{target}"
    if direct in nodes:
        return direct
    # Try with common extensions
    from_dir = str(Path(from_file).parent)
    for ext in [".py", ".js", ".ts", ".go", ".rs", ".java"]:
        candidate = str(Path(from_dir) / (target.replace(".", "/") + ext))
        cid = f"file:{candidate}"
        if cid in nodes:
            return cid
    # Fall back to a module node
    return f"module:{target}"


# ---------------------------------------------------------------------------
# Non-code file parsers
# ---------------------------------------------------------------------------

def parse_markdown(path: Path) -> Tuple[List[dict], List[dict]]:
    """Extract heading hierarchy and links from Markdown."""
    nodes: List[dict] = []
    edges: List[dict] = []
    stack: List[Tuple[int, str]] = []  # (level, node_id)
    file_str = str(path)

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return nodes, edges

    for lineno, line in enumerate(lines, 1):
        m = re.match(r"^(#{1,6})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            heading = m.group(2).strip()
            nid = f"heading:{file_str}:{lineno}:{heading[:40]}"
            nodes.append({"id": nid, "label": heading, "type": f"h{level}", "file": file_str, "line": lineno})

            # Pop stack to find parent
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                edges.append({"source": stack[-1][1], "target": nid, "relation": "contains", "file": file_str, "line": lineno})
            stack.append((level, nid))

        # Extract links
        for lm in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
            link_text = lm.group(1)
            link_target = lm.group(2)
            nid = f"link:{file_str}:{lineno}:{link_text[:30]}"
            target_nid = f"ref:{link_target[:60]}"
            nodes.append({"id": nid, "label": link_text, "type": "link", "file": file_str, "line": lineno})
            nodes.append({"id": target_nid, "label": link_target, "type": "reference", "file": "", "line": 0})
            edges.append({"source": nid, "target": target_nid, "relation": "links_to", "file": file_str, "line": lineno})

    return nodes, edges


def parse_yaml_toml(path: Path) -> Tuple[List[dict], List[dict]]:
    """Extract top-level keys from YAML/TOML files."""
    nodes: List[dict] = []
    edges: List[dict] = []
    file_str = str(path)

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return nodes, edges

    parent_id = f"file:{file_str}"
    for lineno, line in enumerate(lines, 1):
        m = re.match(r"^(\w[\w.-]*)(?:\s*:|\s*=)", line)
        if m:
            key = m.group(1)
            nid = f"key:{file_str}:{lineno}:{key}"
            nodes.append({"id": nid, "label": key, "type": "config_key", "file": file_str, "line": lineno})
            edges.append({"source": parent_id, "target": nid, "relation": "defines", "file": file_str, "line": lineno})

    return nodes, edges


def scan_extra_files(directory: Path) -> Tuple[List[dict], List[dict]]:
    """Walk a directory and parse non-code files (Markdown, YAML, TOML)."""
    all_nodes: List[dict] = []
    all_edges: List[dict] = []
    SKIP = {"node_modules", "__pycache__", ".git", "vendor", "dist", "build", ".venv", "venv"}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for fname in files:
            fpath = Path(root) / fname
            ext = fpath.suffix.lower()
            if ext in (".md",):
                n, e = parse_markdown(fpath)
            elif ext in (".yaml", ".yml", ".toml"):
                n, e = parse_yaml_toml(fpath)
            else:
                continue
            all_nodes.extend(n)
            all_edges.extend(e)

    return all_nodes, all_edges


# ---------------------------------------------------------------------------
# Graph analysis
# ---------------------------------------------------------------------------

def compute_degrees(nodes: Dict[str, dict], edges: List[dict]) -> None:
    for edge in edges:
        if edge["source"] in nodes:
            nodes[edge["source"]]["degree"] = nodes[edge["source"]].get("degree", 0) + 1
        if edge["target"] in nodes:
            nodes[edge["target"]]["degree"] = nodes[edge["target"]].get("degree", 0) + 1


def find_clusters(nodes: Dict[str, dict], edges: List[dict]) -> List[List[str]]:
    """Union-Find connected components."""
    parent = {nid: nid for nid in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        pa, pb = find(a), find(b)
        if pa != pb:
            parent[pa] = pb

    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src in nodes and tgt in nodes:
            union(src, tgt)

    groups: Dict[str, List[str]] = defaultdict(list)
    for nid in nodes:
        groups[find(nid)].append(nid)
    return sorted(groups.values(), key=len, reverse=True)


def detect_architectural_patterns(nodes: Dict[str, dict], edges: List[dict]) -> List[str]:
    """Heuristic pattern detection from node types and naming conventions."""
    patterns = []
    node_labels = [n["label"].lower() for n in nodes.values()]
    node_types = [n["type"] for n in nodes.values()]
    label_str = " ".join(node_labels)

    if any(t in label_str for t in ["controller", "view", "model"]):
        patterns.append("MVC (Model-View-Controller) signals detected")
    if any(t in label_str for t in ["repository", "service", "entity"]):
        patterns.append("Layered architecture (Repository/Service/Entity) signals detected")
    if "interface" in node_types and "class" in node_types:
        patterns.append("Interface-based abstraction in use")
    if any(t in label_str for t in ["handler", "router", "middleware"]):
        patterns.append("HTTP handler / routing layer detected")
    if any(t in label_str for t in ["queue", "worker", "consumer", "producer", "broker"]):
        patterns.append("Event-driven / message queue architecture signals detected")
    if any(t in label_str for t in ["migrate", "migration", "schema"]):
        patterns.append("Database migration layer detected")
    if any(t in label_str for t in ["test", "spec", "mock", "stub", "fixture"]):
        patterns.append("Test infrastructure present")
    if any(t in label_str for t in ["config", "settings", "env", "environment"]):
        patterns.append("Configuration management layer detected")

    return patterns if patterns else ["No dominant architectural pattern detected — may be library/script collection"]


# ---------------------------------------------------------------------------
# Main graph assembly
# ---------------------------------------------------------------------------

def build_graph(
    entities_path: Optional[Path] = None,
    scan_dir: Optional[Path] = None,
) -> dict:
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []

    # Phase 1: code entities from ast_extractor
    if entities_path:
        file_results = load_extractor_output(entities_path)
        code_nodes, code_edges = entities_to_graph(file_results)
        nodes.update(code_nodes)
        edges.extend(code_edges)

    # Phase 2: non-code files
    if scan_dir and scan_dir.is_dir():
        extra_nodes, extra_edges = scan_extra_files(scan_dir)
        for n in extra_nodes:
            if n["id"] not in nodes:
                nodes[n["id"]] = n
        edges.extend(extra_edges)

    # Phase 3: compute metrics
    compute_degrees(nodes, edges)
    clusters = find_clusters(nodes, edges)
    patterns = detect_architectural_patterns(nodes, edges)

    sorted_nodes = sorted(nodes.values(), key=lambda n: n.get("degree", 0), reverse=True)
    hub_nodes = [n for n in sorted_nodes if n.get("degree", 0) > 2][:20]
    orphan_nodes = [n for n in sorted_nodes if n.get("degree", 0) == 0]

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "cluster_count": len(clusters),
            "hub_count": len(hub_nodes),
            "orphan_count": len(orphan_nodes),
        },
        "hub_nodes": hub_nodes,
        "orphan_nodes": orphan_nodes[:20],
        "clusters": [[n for n in cluster[:10]] for cluster in clusters[:5]],
        "patterns": patterns,
    }


SAMPLE_ENTITIES = [
    {
        "file": "src/services/user_service.py",
        "lang": "python",
        "nodes": [
            {"type": "class", "name": "UserService", "line": 1},
            {"type": "function", "name": "get_user", "line": 5},
            {"type": "function", "name": "create_user", "line": 10},
        ],
        "edges": [
            {"from": "src/services/user_service.py", "to": "src/repositories.email_repo", "relation": "imports", "line": 2},
        ],
        "skipped": False,
    },
    {
        "file": "src/repositories/user_repo.py",
        "lang": "python",
        "nodes": [
            {"type": "class", "name": "UserRepository", "line": 1},
            {"type": "function", "name": "find_by_id", "line": 8},
        ],
        "edges": [],
        "skipped": False,
    },
]


def run_sample() -> None:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(SAMPLE_ENTITIES, f)
        tmp = Path(f.name)
    graph = build_graph(entities_path=tmp)
    tmp.unlink()
    print(json.dumps(graph, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a unified knowledge graph from ast_extractor output and non-code files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("entities_json", nargs="?", help="JSON output from ast_extractor.py")
    parser.add_argument("--scan", metavar="DIR", help="Also scan this directory for Markdown/YAML/TOML files")
    parser.add_argument("--sample", action="store_true", help="Run on built-in example and exit")

    args = parser.parse_args()

    if args.sample:
        run_sample()
        return

    if not args.entities_json and not args.scan:
        parser.print_help()
        sys.exit(1)

    entities_path = Path(args.entities_json) if args.entities_json else None
    scan_dir = Path(args.scan) if args.scan else None

    if entities_path and not entities_path.exists():
        print(f"ERROR: entities file not found: {entities_path}", file=sys.stderr)
        sys.exit(1)

    graph = build_graph(entities_path=entities_path, scan_dir=scan_dir)
    print(json.dumps(graph, indent=2))


if __name__ == "__main__":
    main()
