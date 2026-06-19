# Graph Output Template

This file documents the canonical JSON schema for graphify's two intermediate formats.
Use it as a reference when integrating graphify output into downstream pipelines.

## 1. ast_extractor.py Output Schema

One object per file. Array of file objects emitted to stdout.

```json
[
  {
    "file": "src/services/user_service.py",
    "lang": "python",
    "nodes": [
      { "type": "class",    "name": "UserService", "line": 1 },
      { "type": "function", "name": "get_user",    "line": 5 },
      { "type": "import",   "name": "os",          "line": 2 }
    ],
    "edges": [
      {
        "from":     "src/services/user_service.py",
        "to":       "src.repositories.user_repo",
        "relation": "imports",
        "line":     3
      }
    ],
    "skipped":   false,
    "reason":    null,
    "truncated": false
  }
]
```

**Node types by language family:**

| Type | Languages |
|------|-----------|
| `class` | Python, JS, TS, Java, C#, PHP, Swift, Kotlin, Scala, C, C++ |
| `function` / `method` | All languages |
| `interface` | Java, C#, TS, Go, Rust (trait), Swift (protocol) |
| `struct` | Go, Rust, C, C++, Swift |
| `import` / `require` / `using` / `use` | All languages |
| `module` | Python, Ruby, Scala |
| `enum` | Rust, Kotlin, Java |
| `h1` / `h2` / `h3` | Markdown |
| `key` | YAML, TOML, JSON |
| `selector` / `variable` | CSS |
| `table` / `view` | SQL |

---

## 2. graph_builder.py Output Schema

Single unified graph object.

```json
{
  "nodes": [
    {
      "id":     "file:src/services/user_service.py",
      "label":  "user_service.py",
      "type":   "file",
      "file":   "src/services/user_service.py",
      "line":   0,
      "degree": 4
    }
  ],
  "edges": [
    {
      "source":   "file:src/services/user_service.py",
      "target":   "class:src/services/user_service.py:UserService",
      "relation": "contains",
      "file":     "src/services/user_service.py",
      "line":     1
    }
  ],
  "stats": {
    "node_count":    42,
    "edge_count":    87,
    "cluster_count": 3,
    "hub_count":     5,
    "orphan_count":  2
  },
  "hub_nodes": [
    { "id": "...", "label": "...", "type": "file", "degree": 12 }
  ],
  "orphan_nodes": [
    { "id": "...", "label": "...", "type": "function", "degree": 0 }
  ],
  "clusters": [
    ["file:src/services/...", "file:src/repos/..."]
  ],
  "patterns": [
    "Layered architecture (Repository/Service/Entity) signals detected",
    "Test infrastructure present"
  ]
}
```

**Node ID conventions:**

| Pattern | Meaning |
|---------|---------|
| `file:<path>` | Source file |
| `class:<path>:<name>` | Class definition in file |
| `function:<path>:<name>` | Function/method in file |
| `module:<name>` | Resolved external module |
| `external:<name>` | Unresolved external (library) |
| `heading:<path>:<line>:<label>` | Markdown heading |
| `key:<path>:<line>:<name>` | YAML/TOML config key |
| `ref:<url>` | External URL reference |

**Relation types:**

| Relation | Meaning |
|----------|---------|
| `contains` | File → entity, heading → sub-heading |
| `imports` | Module import / require statement |
| `extends` | Class inheritance |
| `implements` | Interface implementation |
| `calls` | Function call (requires full call-graph analysis) |
| `links_to` | Markdown link → referenced URL |
| `defines` | Config file → key |

---

## 3. Extending the Schema

To add nodes from external sources (Claude multimodal extraction, Whisper transcripts):

```json
[
  {
    "id":     "concept:design-session:UserAuthFlow",
    "label":  "User Auth Flow",
    "type":   "concept",
    "file":   "design-session.mp4",
    "line":   0,
    "degree": 0
  }
]
```

Pass as `--merge extra_nodes.json` to `graph_builder.py` to incorporate into the unified graph before rendering.
