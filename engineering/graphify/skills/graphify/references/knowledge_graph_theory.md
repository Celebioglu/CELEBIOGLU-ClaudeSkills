# Knowledge Graph Theory — Reference

## What is a Knowledge Graph?

A knowledge graph represents entities (nodes) and relationships (edges) in a domain. For software systems: entities are files, classes, functions, modules, and concepts; relationships are imports, calls, extends, contains, and links_to.

## Foundational Sources

**1. Ehrlinger & Wöß (2016) — "Towards a Definition of Knowledge Graphs"**  
*Semantics 2016 / CEUR Workshop Proceedings Vol-1695*  
Defines KGs as a graph of real-world entities and relationships, intended to accumulate and convey knowledge of the real world. Key insight: a knowledge graph is not just a schema — it accumulates instance data. For codebases this means both structure (classes/functions) and behavior (call graphs, dependency chains) belong in the graph.

**2. Hogan et al. (2021) — "Knowledge Graphs"**  
*ACM Computing Surveys 54(4)*  
Comprehensive survey covering: graph data models (RDF, property graphs, labelled graphs), deductive closures (what you can infer), and inductive closures (what you can learn). For code analysis: labelled property graphs are the practical model — each node/edge has typed attributes (language, line number, degree).

**3. Guo et al. (2020) — "A Survey on Knowledge Graph-Based Recommender Systems"**  
*IEEE Transactions on Knowledge and Data Engineering 34(8)*  
Demonstrates that KG structure (hub identification, path reasoning) is itself a source of insight, independent of LLM synthesis. Hub nodes in a software KG correspond to high-blast-radius components — the same centrality reasoning applies.

**4. NetworkX Documentation — Graph Theory in Python**  
*networkx.org*  
Reference implementation for connected components, degree centrality, clustering coefficients, and shortest-path algorithms. The Union-Find cluster algorithm in `graph_builder.py` follows the same connected-components logic. For graphs > 10k nodes, NetworkX's built-in algorithms outperform custom implementations.

**5. Barabási & Albert (1999) — "Emergence of Scaling in Random Networks"**  
*Science 286(5439)*  
Power-law degree distribution: in real-world networks (including codebases), a small number of nodes have very high degree (hubs) while most have low degree. This is why `graph_renderer.py` surfaces hub nodes first — they are the architectural load-bearers.

**6. Freeman (1977) — "A Set of Measures of Centrality Based on Betweenness"**  
*Sociometry 40(1)*  
Defines betweenness centrality: a node is central if many shortest paths pass through it. In a codebase, high-betweenness files are chokepoints — breaking them breaks many paths. Future graphify extension: implement betweenness centrality for deeper architectural risk scoring.

**7. Watts & Strogatz (1998) — "Collective dynamics of 'small-world' networks"**  
*Nature 393*  
Small-world networks have short average path lengths and high clustering — most real codebases exhibit this structure (many tightly-coupled clusters with a few cross-cutting hubs). Recognizing this pattern explains why modular refactors are hard: the clusters are self-reinforcing.

## Practical Implications for Graphify

| Concept | Graphify behavior |
|---------|------------------|
| Hub nodes (high degree) | Surfaced first in all renderers — highest change risk |
| Orphan nodes (degree 0) | Listed separately — dead code candidates or missing wiring |
| Connected components | Shown as clusters — each is a candidate for independent deployment |
| Power-law distribution | Expected — most files have 1-2 edges; don't panic at the long tail |
| Small-world property | High cluster count + short hub paths = monolith tendency |

## Anti-Patterns in Knowledge Graph Design

- **Over-granularity:** graphing every variable and parameter produces noise, not insight. graphify stops at class/function level by default.
- **Ignoring edge direction:** imports are directed (A imports B ≠ B imports A). `graph_builder.py` preserves directionality.
- **Conflating structural and semantic edges:** "contains" (file → class) and "imports" (file → dependency) are qualitatively different. Both are included but styled differently in renderers.
- **Missing external nodes:** external library imports are still nodes in the graph (type: external) — they show which third-party dependencies are hubs.
