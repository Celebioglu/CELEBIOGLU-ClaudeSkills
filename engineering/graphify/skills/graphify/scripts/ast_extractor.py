#!/usr/bin/env python3
"""
ast_extractor.py — Extract code entities (nodes + edges) from source files.

Stdlib regex parsing for 25 languages. Optional tree-sitter for richer AST:
  pip install tree-sitter tree-sitter-python tree-sitter-javascript ...

Usage:
  python ast_extractor.py <path>            # file or directory
  python ast_extractor.py <path> --lang py  # force language
  python ast_extractor.py <path> --format text
  python ast_extractor.py --sample          # run on built-in example
  python ast_extractor.py --help
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LANG_BY_EXT: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin", ".kts": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".lua": "lua",
    ".sh": "bash", ".bash": "bash",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "css", ".less": "css",
    ".sql": "sql",
    ".yaml": "yaml", ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".cs": "csharp",
}

# Regex patterns per language: (entity_type, regex, name_group_index)
PATTERNS: Dict[str, List[Tuple[str, str, int]]] = {
    "python": [
        ("class",    r"^class\s+(\w+)",                          1),
        ("function", r"^(?:async\s+)?def\s+(\w+)",               1),
        ("import",   r"^import\s+([\w.]+)",                       1),
        ("import",   r"^from\s+([\w.]+)\s+import",               1),
        ("variable", r"^(\w+)\s*=\s*(?!.*lambda)",               1),
    ],
    "javascript": [
        ("class",    r"(?:^|\s)class\s+(\w+)",                   1),
        ("function", r"(?:^|\s)function\s+(\w+)",                 1),
        ("function", r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(",  1),
        ("import",   r"^import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", 1),
        ("import",   r"^(?:const|let|var)\s+\w+\s*=\s*require\(['\"]([^'\"]+)['\"]\)", 1),
        ("export",   r"^export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)", 1),
    ],
    "typescript": [
        ("interface", r"(?:^|\s)interface\s+(\w+)",              1),
        ("type",      r"(?:^|\s)type\s+(\w+)\s*=",              1),
        ("class",     r"(?:^|\s)class\s+(\w+)",                  1),
        ("function",  r"(?:^|\s)function\s+(\w+)",               1),
        ("function",  r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(", 1),
        ("import",    r"^import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", 1),
        ("export",    r"^export\s+(?:default\s+)?(?:class|interface|type|function|const)\s+(\w+)", 1),
    ],
    "java": [
        ("class",     r"(?:^|\s)(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?class\s+(\w+)", 1),
        ("interface", r"(?:^|\s)(?:public\s+)?interface\s+(\w+)", 1),
        ("method",    r"(?:public|private|protected|static|final|synchronized)[\w\s<>[\]]*\s+(\w+)\s*\(", 1),
        ("import",    r"^import\s+([\w.]+);",                    1),
    ],
    "go": [
        ("struct",    r"^type\s+(\w+)\s+struct",                 1),
        ("interface", r"^type\s+(\w+)\s+interface",              1),
        ("function",  r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", 1),
        ("import",    r"\"([\w./]+)\"",                          1),
    ],
    "rust": [
        ("struct",    r"(?:^|\s)(?:pub\s+)?struct\s+(\w+)",     1),
        ("enum",      r"(?:^|\s)(?:pub\s+)?enum\s+(\w+)",       1),
        ("trait",     r"(?:^|\s)(?:pub\s+)?trait\s+(\w+)",      1),
        ("function",  r"(?:^|\s)(?:pub\s+)?fn\s+(\w+)\s*[<(]",  1),
        ("import",    r"^use\s+([\w::]+)",                       1),
    ],
    "ruby": [
        ("class",    r"^class\s+(\w+)",                          1),
        ("module",   r"^module\s+(\w+)",                         1),
        ("method",   r"^\s*def\s+(\w+)",                         1),
        ("require",  r"require(?:_relative)?\s+['\"]([^'\"]+)['\"]", 1),
    ],
    "csharp": [
        ("class",     r"(?:public|private|protected|internal)?\s+(?:abstract\s+|sealed\s+)?class\s+(\w+)", 1),
        ("interface", r"(?:public|private|protected|internal)?\s+interface\s+(\w+)", 1),
        ("method",    r"(?:public|private|protected|internal|static|virtual|override)[\w\s<>[\]]*\s+(\w+)\s*\(", 1),
        ("using",     r"^using\s+([\w.]+);",                     1),
    ],
    "swift": [
        ("class",    r"(?:open\s+|public\s+|internal\s+|fileprivate\s+|private\s+)?class\s+(\w+)", 1),
        ("struct",   r"(?:open\s+|public\s+|internal\s+)?struct\s+(\w+)", 1),
        ("protocol", r"(?:public\s+)?protocol\s+(\w+)",          1),
        ("function", r"(?:public\s+|private\s+|internal\s+)?func\s+(\w+)\s*[<(]", 1),
        ("import",   r"^import\s+(\w+)",                         1),
    ],
    "kotlin": [
        ("class",    r"(?:open\s+|data\s+|sealed\s+)?class\s+(\w+)", 1),
        ("interface",r"interface\s+(\w+)",                       1),
        ("function", r"(?:fun\s+)(\w+)\s*[<(]",                  1),
        ("import",   r"^import\s+([\w.]+)",                      1),
    ],
    "php": [
        ("class",    r"(?:abstract\s+|final\s+)?class\s+(\w+)",  1),
        ("interface",r"interface\s+(\w+)",                       1),
        ("function", r"function\s+(\w+)\s*\(",                   1),
        ("use",      r"^use\s+([\w\\]+)",                        1),
    ],
    "scala": [
        ("class",   r"(?:case\s+)?class\s+(\w+)",               1),
        ("object",  r"(?:case\s+)?object\s+(\w+)",              1),
        ("trait",   r"trait\s+(\w+)",                            1),
        ("def",     r"def\s+(\w+)\s*[(\[:]",                    1),
        ("import",  r"^import\s+([\w._]+)",                     1),
    ],
    "markdown": [
        ("h1",      r"^#\s+(.+)",                                1),
        ("h2",      r"^##\s+(.+)",                               1),
        ("h3",      r"^###\s+(.+)",                              1),
        ("link",    r"\[([^\]]+)\]\(([^)]+)\)",                  1),
    ],
    "yaml": [
        ("key",     r"^(\w[\w.-]*):",                            1),
    ],
    "json": [],   # handled separately
    "toml": [
        ("section", r"^\[([^\]]+)\]",                            1),
        ("key",     r"^(\w[\w.-]*)\s*=",                         1),
    ],
    "sql": [
        ("table",   r"(?:CREATE|create)\s+TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)", 1),
        ("view",    r"(?:CREATE|create)\s+VIEW\s+(\w+)",         1),
        ("function",r"(?:CREATE|create)\s+FUNCTION\s+(\w+)",     1),
    ],
    "html": [
        ("id",      r'id=["\']([^"\']+)["\']',                   1),
        ("class",   r'class=["\']([^"\']+)["\']',                1),
    ],
    "css": [
        ("selector", r"^([.#]?[\w-]+(?:\s*,\s*[.#]?[\w-]+)*)\s*\{", 1),
        ("variable", r"^(--[\w-]+)\s*:",                         1),
    ],
    "bash": [
        ("function", r"^(\w+)\s*\(\)\s*\{",                     1),
        ("variable", r"^(\w+)=",                                  1),
        ("source",   r"(?:source|\.)(?:\s+)([^\s;]+)",           1),
    ],
    "c": [
        ("function", r"^(?:static\s+|extern\s+)?[\w*]+\s+(\w+)\s*\([^;]*\)\s*\{", 1),
        ("struct",   r"struct\s+(\w+)\s*\{",                    1),
        ("include",  r"^#include\s+[<\"]([^>\"]+)[>\"]",         1),
        ("define",   r"^#define\s+(\w+)",                        1),
    ],
    "cpp": [
        ("class",    r"(?:class|struct)\s+(\w+)\s*[:{]",        1),
        ("function", r"^(?:[\w:*&<>]+\s+)+(\w+)\s*\([^;]*\)\s*(?:const\s*)?\{", 1),
        ("namespace",r"namespace\s+(\w+)\s*\{",                  1),
        ("include",  r"^#include\s+[<\"]([^>\"]+)[>\"]",         1),
    ],
    "lua": [
        ("function", r"^(?:local\s+)?function\s+([\w.]+)\s*\(", 1),
        ("require",  r"require\s*[\(\s]['\"]([^'\"]+)['\"]",     1),
    ],
    "r": [
        ("function", r"(\w+)\s*<-\s*function\s*\(",             1),
        ("library",  r"(?:library|require)\s*\(\s*['\"]?(\w+)['\"]?\s*\)", 1),
    ],
}


def detect_language(path: Path, override: Optional[str] = None) -> Optional[str]:
    if override:
        return override
    name = path.name.lower()
    if name == "dockerfile":
        return "dockerfile"
    return LANG_BY_EXT.get(path.suffix.lower())


def extract_json_keys(text: str, max_depth: int = 3) -> List[dict]:
    """Extract top-level keys from JSON."""
    nodes = []
    try:
        import json as _json
        data = _json.loads(text)
        if isinstance(data, dict):
            for key in list(data.keys())[:50]:
                nodes.append({"type": "key", "name": str(key), "line": 0})
    except Exception:
        for m in re.finditer(r'"(\w[\w.-]*)"\s*:', text):
            nodes.append({"type": "key", "name": m.group(1), "line": 0})
    return nodes


def extract_from_file(path: Path, lang: Optional[str] = None, max_lines: int = 5000) -> dict:
    lang = detect_language(path, lang)
    result = {
        "file": str(path),
        "lang": lang or "unknown",
        "nodes": [],
        "edges": [],
        "skipped": False,
        "reason": None,
    }

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result["skipped"] = True
        result["reason"] = str(e)
        return result

    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        result["truncated"] = True

    if lang == "json":
        result["nodes"] = extract_json_keys(text)
        return result

    if lang not in PATTERNS:
        result["skipped"] = True
        result["reason"] = f"No patterns for lang '{lang}'"
        return result

    patterns = PATTERNS[lang]
    seen_names = set()

    for lineno, line in enumerate(lines, 1):
        for entity_type, pattern, group_idx in patterns:
            m = re.search(pattern, line)
            if m:
                try:
                    name = m.group(group_idx).strip()
                except IndexError:
                    continue
                if not name or name in seen_names:
                    continue
                seen_names.add(name)
                node = {"type": entity_type, "name": name, "line": lineno}
                result["nodes"].append(node)

                # Build edges: import → target file/module
                if entity_type in ("import", "require", "using", "use", "source", "include"):
                    result["edges"].append({
                        "from": str(path),
                        "to": name,
                        "relation": "imports",
                        "line": lineno,
                    })

    return result


def extract_from_path(
    path: Path,
    lang: Optional[str] = None,
    depth: int = 10,
    max_lines: int = 5000,
    current_depth: int = 0,
) -> List[dict]:
    results = []
    if path.is_file():
        results.append(extract_from_file(path, lang, max_lines))
    elif path.is_dir() and current_depth < depth:
        try:
            entries = sorted(path.iterdir())
        except PermissionError:
            return results
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.name in ("node_modules", "__pycache__", ".git", "vendor", "dist", "build", ".venv", "venv"):
                continue
            results.extend(extract_from_path(entry, lang, depth, max_lines, current_depth + 1))
    return results


def try_treesitter(path: Path) -> Optional[dict]:
    """Try tree-sitter extraction. Returns None if unavailable."""
    try:
        import tree_sitter  # noqa
    except ImportError:
        return None
    return None  # Placeholder — extend when tree-sitter grammars are installed


def print_text_summary(results: List[dict]) -> None:
    total_nodes = sum(len(r["nodes"]) for r in results)
    total_edges = sum(len(r["edges"]) for r in results)
    print(f"Files scanned : {len(results)}")
    print(f"Total nodes   : {total_nodes}")
    print(f"Total edges   : {total_edges}")
    print()
    for r in results:
        if r["nodes"]:
            print(f"  {r['file']} [{r['lang']}] — {len(r['nodes'])} nodes, {len(r['edges'])} edges")
            for n in r["nodes"][:5]:
                print(f"    {n['type']:12s} {n['name']} (line {n['line']})")
            if len(r["nodes"]) > 5:
                print(f"    ... and {len(r['nodes']) - 5} more")


SAMPLE_CODE = '''
class UserService:
    def __init__(self, db):
        self.db = db

    def get_user(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id={user_id}")

    async def create_user(self, name: str, email: str):
        pass

import os
import json
from pathlib import Path
from services.email import send_welcome
'''


def run_sample() -> None:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(SAMPLE_CODE)
        tmp = Path(f.name)
    result = extract_from_file(tmp, "python")
    tmp.unlink()
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract code entities from source files as a knowledge graph.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", help="File or directory to scan")
    parser.add_argument("--lang", help="Force language (e.g. python, javascript)")
    parser.add_argument("--depth", type=int, default=10, help="Max directory recursion depth (default 10)")
    parser.add_argument("--max-lines", type=int, default=5000, help="Max lines per file (default 5000)")
    parser.add_argument("--format", choices=["json", "text"], default="json", help="Output format")
    parser.add_argument("--sample", action="store_true", help="Run on built-in Python example and exit")

    args = parser.parse_args()

    if args.sample:
        run_sample()
        return

    if not args.path:
        parser.print_help()
        sys.exit(1)

    target = Path(args.path)
    if not target.exists():
        print(f"ERROR: path not found: {target}", file=sys.stderr)
        sys.exit(1)

    results = extract_from_path(target, args.lang, args.depth, args.max_lines)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print_text_summary(results)


if __name__ == "__main__":
    main()
