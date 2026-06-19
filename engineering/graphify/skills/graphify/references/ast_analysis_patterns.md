# AST Analysis Patterns — Reference

## What is an AST?

An Abstract Syntax Tree (AST) is the parsed structure of source code — a tree where each node represents a syntactic construct (class, function, import, expression). `ast_extractor.py` builds a subset of a full AST: it extracts named entities and their line numbers without full parse-tree fidelity.

## Why Regex Over Full AST?

graphify uses regex-based entity extraction (stdlib) with optional tree-sitter upgrade. The tradeoff:

| Approach | Pros | Cons |
|---------|------|------|
| Stdlib regex | Zero deps, fast, works everywhere | Misses nested definitions, no type info |
| tree-sitter | Accurate parse tree, handles nesting | Requires per-language grammar packages |
| Python `ast` module (Python-only) | Exact AST, stdlib | Python files only |

For the 80%-case (finding architectural structure), regex is sufficient. Enable tree-sitter for precise call-graph extraction.

## Foundational Sources

**1. Aho, Lam, Sethi & Ullman (2006) — "Compilers: Principles, Techniques, and Tools" (Dragon Book)**  
*Addison-Wesley, 2nd edition*  
The canonical reference for lexing, parsing, and AST construction. Chapters 2-3 cover context-free grammars and parse trees. The regex patterns in `ast_extractor.py` are simplified recognizers (regular grammars) — they handle most class/function declarations but cannot handle context-sensitive constructs like Python decorators spanning multiple lines.

**2. tree-sitter Project — Incremental Parsing**  
*tree-sitter.github.io*  
tree-sitter uses a generalized LR parser to produce concrete syntax trees incrementally. Key properties: error recovery (parses broken code), incremental update (only re-parses changed nodes), 29+ language grammars. For graphify: `pip install tree-sitter` + per-language grammar enables `try_treesitter()` in `ast_extractor.py` to override the regex fallback.

**3. Lopes et al. (2017) — "DéjàVu: A Map of Code Duplicates on GitHub"**  
*OOPSLA 2017, ACM*  
Analyzed 428M files across 4.5M repos. Finding: 70% of code files on GitHub are near-duplicates of other files. Implication for graphify: high orphan counts in a scan are often copy-pasted files that import nothing and export nothing — valuable signal for cleanup.

**4. Binkley & Harman (2004) — "A Survey of Empirical Results on Program Slicing"**  
*Advances in Computers 62*  
Program slicing identifies the subset of code that can affect a variable at a point. graphify's hub node detection is a structural approximation: hub nodes are likely to appear in many slices. This makes them high-priority candidates for refactoring to reduce coupling.

**5. Hassan (2008) — "The Road Ahead for Mining Software Repositories"**  
*Frontiers of Software Maintenance, IEEE*  
Defines software repository mining as the extraction of actionable information from version history, code, and communication artifacts. graphify operates on the "static snapshot" tier — structure at a point in time. Future extension: git log analysis to identify which nodes change most often (churn), intersected with hub degree.

**6. Palsberg & Schwartzbach (1991) — "Object-Oriented Type Inference"**  
*OOPSLA 1991*  
Type inference in OOP languages requires tracking class hierarchies and method dispatch. graphify records `extends` edges when detectable from class declarations (`class Foo extends Bar`) — richer type flow analysis requires full type inference (tree-sitter + language server).

**7. Zimmermann et al. (2008) — "Predicting Defects for Eclipse"**  
*ICSE 2008 Workshop on Predictor Models in Software Engineering*  
Finding: coupling metrics (fan-in, fan-out) are strong predictors of defect density. graphify's hub nodes (high fan-in) are exactly the high-defect-risk candidates. Rule of thumb from this paper: files with fan-in > 10 have 2-4x higher defect rates.

## Language-Specific Notes

### Python
- `ast_extractor.py` uses line-anchored patterns (`^`) so it only catches top-level definitions. Nested classes/functions inside methods are not extracted.
- Python's `ast` module (stdlib) gives exact AST: `import ast; tree = ast.parse(source)`. For a pure-Python-codebase deep-dive, consider post-processing with `ast.walk()`.

### JavaScript / TypeScript
- Arrow function patterns (`const fn = () => {}`) are partially matched. Complex destructuring assignments are not.
- ESM and CommonJS import patterns are both supported.
- TypeScript generics (e.g., `class Foo<T>`) extract the base name (`Foo`), not the type parameter.

### Go
- Interface declarations and struct definitions are extracted. Method receivers (e.g., `func (u *User) Save()`) extract the method name (`Save`), not the receiver type. The receiver creates an implicit edge in the call graph that regex cannot capture — use tree-sitter for accurate Go analysis.

### Rust
- Macro invocations (`macro_rules! foo`) are not extracted. `impl Trait for Type` blocks are not parsed — only the inner `fn` declarations are captured.

## Enabling tree-sitter (Optional)

```bash
pip install tree-sitter
# Per-language grammars:
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
pip install tree-sitter-go tree-sitter-rust tree-sitter-java
```

Once installed, `ast_extractor.py`'s `try_treesitter()` function activates automatically and overrides regex output for supported languages. The JSON schema is identical — downstream tools are unaffected.
