# graphify — Knowledge Graph for Any Codebase or File Collection

Build a knowledge graph from any codebase or file collection. Surface hidden structure, hub nodes (blast radius), orphaned files (dead code), connected clusters (coupling), and architectural patterns — without reading every file manually.

## Quick Start

```bash
# In Claude Code, Codex, Cursor, Gemini CLI, or any supported AI assistant:
/graphify ./src

# Or install as a plugin:
# Claude Code: add this folder path to your .claude/plugins.json
# Codex CLI:   add this folder path to your codex.yaml plugins section
```

## What It Does

```
/graphify <path>
       │
       ├── ast_extractor.py   → scans code files (25 langs), extracts classes/functions/imports
       │
       ├── graph_builder.py   → merges all sources, computes hub nodes, orphans, clusters
       │                         also parses Markdown headings, YAML/TOML keys
       │
       └── graph_renderer.py  → outputs: Mermaid | DOT | ASCII | JSON | summary
```

## Supported Inputs

| Type | How |
|------|-----|
| Code (25 languages) | `ast_extractor.py` — stdlib regex + optional tree-sitter |
| Markdown / docs | `graph_builder.py` — heading hierarchy |
| JSON / YAML / TOML | `graph_builder.py` — key extraction |
| Images / diagrams / screenshots | Claude multimodal (native, no install) |
| PDFs | `pdfminer.six` (optional) or Claude multimodal |
| Audio / video | Whisper local transcription (CPU, no API key) |

## Supported AI Assistants

Works anywhere you can load a `.claude-plugin/` skill:

- **Claude Code** (CLI + web + VS Code extension)
- **OpenAI Codex CLI**
- **OpenCode**
- **Cursor**
- **Gemini CLI**
- **GitHub Copilot CLI**
- **VS Code Copilot Chat**
- **Aider**
- **OpenClaw**
- **Factory Droid**
- **Trae**
- **Hermes Agent**
- **Kiro**
- **Google Antigravity**

Type `/graphify` in any of these tools to activate.

## Output Formats

```bash
/graphify ./src --format summary  # plain English insight report (default)
/graphify ./src --format mermaid  # paste into Claude chat for visual graph
/graphify ./src --format dot      # compile with dot -Tsvg for SVG
/graphify ./src --format ascii    # terminal-friendly adjacency list
/graphify ./src --format json     # hub nodes + stats for downstream tools
```

## Example Output

```
GRAPHIFY RESULTS — ./src
═══════════════════════════════════════
Nodes    : 142
Edges    : 287
Clusters : 3
Hubs     : 8  (degree > 2)
Orphans  : 4

TOP HUB NODES
  1. user_service.py  (file, degree=12) — src/services/user_service.py
  2. db_connection.py (file, degree=9)  — src/core/db_connection.py
  3. UserService      (class, degree=7) — src/services/user_service.py

ARCHITECTURAL PATTERNS DETECTED
  • Layered architecture (Repository/Service/Entity) signals detected
  • Test infrastructure present

RECOMMENDED NEXT STEPS
  1. user_service.py is the highest-risk file — 12 files depend on it.
  2. 4 orphan nodes found: utils/legacy_parser.py, helpers/old_auth.py — review for removal.
  3. Run with --format mermaid and paste into Claude for visual navigation.
```

## Files

```
engineering/graphify/
├── .claude-plugin/plugin.json          # Plugin manifest
├── agents/cs-graphify.md               # cs-graphify persona agent
├── commands/cs-graphify.md             # /graphify slash command
├── skills/graphify/
│   ├── SKILL.md                        # Master documentation
│   ├── scripts/
│   │   ├── ast_extractor.py            # Entity extraction (25 languages)
│   │   ├── graph_builder.py            # Graph assembly + pattern detection
│   │   └── graph_renderer.py           # Multi-format output
│   ├── references/
│   │   ├── knowledge_graph_theory.md   # KG theory (7 sources)
│   │   ├── ast_analysis_patterns.md    # AST patterns (7 sources)
│   │   └── multimodal_extraction.md    # Multimodal pipeline (7 sources)
│   └── assets/
│       └── graph_output_template.md    # JSON schema reference
└── README.md
```

## Dependencies

All scripts run with stdlib only. Optional enhancements:

```bash
pip install tree-sitter              # richer AST (25 language grammars)
pip install openai-whisper           # local audio/video transcription (no API key)
pip install pdfminer.six             # PDF text extraction
```

## License

MIT
