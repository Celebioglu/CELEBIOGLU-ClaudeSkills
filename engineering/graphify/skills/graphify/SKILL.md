---
name: graphify
description: Build a knowledge graph from any codebase or file collection and surface hidden structure, architectural patterns, and the "why" behind decisions. Use when exploring an unfamiliar codebase, preparing for an architecture review, debugging a tangled dependency chain, or onboarding to a new project. Supports code (25 languages via tree-sitter AST), Markdown, JSON/YAML, PDF, images, screenshots, diagrams, and audio/video (Whisper transcription). Works in Claude Code, Codex, OpenCode, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, and Google Antigravity — type /graphify to run.
version: 1.0.0
---

# Graphify — Knowledge Graph for Any Codebase or File Collection

## Quick Start

```bash
# Extract AST entities from a codebase
python scripts/ast_extractor.py ./src --format json > entities.json

# Build the unified knowledge graph
python scripts/graph_builder.py entities.json --scan ./src > graph.json

# Render to Mermaid / DOT / ASCII / JSON summary
python scripts/graph_renderer.py graph.json --format mermaid
```

## Workflows

### Workflow 1: Understand a new codebase (10 min)

1. Run `ast_extractor.py <path>` to scan all code files — outputs nodes (classes, functions, modules) and edges (imports, calls, inheritance).
2. Run `graph_builder.py <entities.json>` — merges entities, detects hub nodes (most connected), orphans, and clusters.
3. Run `graph_renderer.py <graph.json> --format mermaid` — paste into any Mermaid viewer or Claude chat.
4. Ask Claude: "What architectural pattern does this graph suggest? Where are the single points of failure?"

### Workflow 2: Multimodal session (code + docs + images)

1. Drop any mix of files into the chat: code files, PDFs, screenshots, whiteboard photos, diagrams, audio/video recordings.
2. Claude extracts concepts and relationships from each source — code via `ast_extractor.py`; docs via heading/section parsing; images and video natively (multimodal); audio via Whisper (local, no cloud).
3. Run `graph_builder.py --merge` to unify all extracted entities into one graph.
4. Run `graph_renderer.py --format summary` for a plain-language insight report.

### Workflow 3: Architecture archaeology

```bash
# Find the most connected (hub) nodes — where changes have the widest blast radius
python scripts/graph_renderer.py graph.json --format summary --top-hubs 10

# Find orphaned files/modules — dead code candidates
python scripts/graph_renderer.py graph.json --format summary --orphans

# Export DOT for GraphViz visualization
python scripts/graph_renderer.py graph.json --format dot > codebase.dot
dot -Tsvg codebase.dot -o codebase.svg
```

## Supported Input Types

| Type | How processed |
|------|--------------|
| Code (25 langs) | `ast_extractor.py` via regex + optional tree-sitter |
| Markdown / docs | Heading hierarchy → concept graph |
| JSON / YAML / TOML | Schema keys → entity graph |
| Images / screenshots | Claude multimodal — concepts extracted natively |
| PDF | Text extraction → heading/entity graph |
| Audio / video | Whisper local transcription → concept graph |

## Forcing Questions (run before any /graphify session)

1. **What do you already know?** Name the entry point (main file, root package, service boundary) — graphify starts faster with a hint.
2. **What are you trying to decide?** "Find what's tangled" vs "find what's dead" vs "find the blast radius of change X" each need different renderer flags.
3. **How big is the target?** > 10k files: use `--depth 2` to limit traversal. < 100 files: scan everything.
4. **Are there non-code assets?** List them — PDFs, images, recordings — so Claude knows to apply multimodal extraction.
5. **What format do you need?** Mermaid (chat-ready), DOT (GraphViz), JSON (pipeline), ASCII (terminal), summary (plain English).

## Dependencies

- **Stdlib (always available):** `ast_extractor.py`, `graph_builder.py`, `graph_renderer.py`
- **Optional, richer AST:** `pip install tree-sitter` + language grammars (documented in `references/ast_analysis_patterns.md`)
- **Optional, local video/audio:** `pip install openai-whisper` (CPU-only, no cloud API key needed)
- **Optional, PDF text:** `pip install pdfminer.six` (or pass PDF to Claude directly for multimodal extraction)

See `references/` for canonical sources, `assets/graph_output_template.md` for output format spec.
