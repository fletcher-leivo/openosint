# Graph Report - openosint  (2026-07-21)

## Corpus Check
- 131 files · ~603,421 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5 nodes · 6 edges · 1 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0f705fab`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- load-vault-secrets.sh

## God Nodes (most connected - your core abstractions)
1. `load-vault-secrets.sh script` - 3 edges
2. `load_optional()` - 2 edges
3. `load_critical()` - 2 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (1 total, 0 thin omitted)

### Community 0 - "load-vault-secrets.sh"
Cohesion: 0.60
Nodes (3): load_critical(), load_optional(), load-vault-secrets.sh script

## Suggested Questions
_Not enough signal to generate questions. This usually means the corpus has no AMBIGUOUS edges, no bridge nodes, no INFERRED relationships, and all communities are tightly cohesive. Add more files or run with --mode deep to extract richer edges._