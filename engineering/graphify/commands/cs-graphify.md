---
name: "cs-graphify"
description: "/graphify <path> — Build a knowledge graph from a codebase or file collection. Reads code (25 languages), Markdown, JSON/YAML, images, PDFs, and audio/video. Surfaces hub nodes (blast radius), orphans (dead code), clusters (coupling), and architectural patterns. Use when exploring an unfamiliar codebase, preparing for an architecture review, debugging tangled dependencies, or onboarding to a new project."
---

# /graphify — Knowledge Graph Command

**Command:** `/graphify <path> [--format mermaid|dot|ascii|json|summary] [--depth N] [--top-hubs N] [--orphans]`

## Pre-flight Gates (run in order — stop at first failure)

**Gate 1 — Path exists:**
```bash
test -e "<path>" || echo "ERROR: path not found"
```
Exit with instructions to provide a valid path if missing.

**Gate 2 — Supported files present:**
```bash
python skills/graphify/scripts/ast_extractor.py "<path>" --format text 2>&1 | head -5
```
If 0 files scanned, warn user that no supported file types were found.

**Gate 3 — Scripts pass self-test:**
```bash
python skills/graphify/scripts/ast_extractor.py --sample > /dev/null && \
python skills/graphify/scripts/graph_builder.py --sample > /dev/null && \
python skills/graphify/scripts/graph_renderer.py --sample > /dev/null && \
echo "SCRIPTS OK"
```

**Gate 4 — Size check:**
If path is a directory, count files:
```bash
find "<path>" -type f | wc -l
```
If > 10,000 files: recommend `--depth 2` and confirm before proceeding.

## Pipeline

```bash
# Step 1: Extract entities from code files
python skills/graphify/scripts/ast_extractor.py "<path>" --format json > /tmp/graphify_entities.json

# Step 2: Build unified graph (also scans Markdown/YAML/TOML)
python skills/graphify/scripts/graph_builder.py /tmp/graphify_entities.json --scan "<path>" > /tmp/graphify_graph.json

# Step 3: Render output
python skills/graphify/scripts/graph_renderer.py /tmp/graphify_graph.json \
  --format <format> \
  --top-hubs <N> \
  [--orphans]
```

## Output Digest

After running, always output this digest:

```
GRAPHIFY RESULTS — <path>
═══════════════════════════════════════
Nodes    : <node_count>
Edges    : <edge_count>
Clusters : <cluster_count>
Hubs     : <hub_count>  (degree > 2)
Orphans  : <orphan_count>

TOP HUB NODES
  1. <label> (<type>, degree=<N>) — <file>
  2. ...

ARCHITECTURAL PATTERNS DETECTED
  • <pattern>

GRAPH OUTPUT
───────────────────────────────────────
<mermaid/dot/ascii/summary output here>

RECOMMENDED NEXT STEPS
  1. ...
  2. ...
```

## Format Guide

| Flag | Best for | Notes |
|------|---------|-------|
| `--format summary` | First run, decision-making | Default. Plain English. |
| `--format mermaid` | Sharing in Claude chat | Paste directly into this conversation |
| `--format dot` | Large graphs, offline viz | Pipe to `dot -Tsvg > out.svg` |
| `--format ascii` | Terminal, CI output | No external tools needed |
| `--format json` | Programmatic use, piping | Hub nodes + stats only |

## Multimodal Mode

When files beyond code are mentioned (images, PDFs, audio, video), activate multimodal mode:

1. Ask: "Drop the image/PDF/recording into this chat."
2. Ask Claude to extract entities and relationships from each file:
   > "Extract entities and relationships from this [image/PDF/transcript] as JSON:
   > `{ "nodes": [{"id": "...", "label": "...", "type": "..."}], "edges": [...] }`"
3. Save Claude's output to `/tmp/extra_nodes.json`.
4. Note: `graph_builder.py --merge` flag is a planned extension — for now, present the multimodal nodes as a separate section in the summary alongside the code graph output.

## Routing

After graphify output:

- **Architecture looks tangled?** → `/cs:grill-me` — pressure-test a refactoring plan
- **Hub nodes are risky?** → `/chaos-experiment` — design a chaos experiment around the hub
- **Want to track changes over time?** → `/cs:handoff` — save the graph summary as a handoff for next session
- **Dead code confirmed?** → `/cs:karpathy-check` — validate removal before deleting

## Related

- Agent: [`cs-graphify`](../agents/cs-graphify.md)
- Skill: [`skills/graphify/SKILL.md`](../skills/graphify/SKILL.md)

---

**Version:** 1.0.0
