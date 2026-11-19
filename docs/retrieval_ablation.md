# Retrieval ablation: query expansion + cross-encoder re-ranking

Questions: `data/eval/questions_draft.jsonl` - 35 answerable (DRAFT, provisional). Tier-stratified hybrid, 3 chunks per tier (9 in context) unless stated. No LLM involved; deterministic.

| Metric | A. hybrid_stratified (before) | B. + query expansion | C. + rerank (MiniLM-L6) | D. + expansion + rerank (MiniLM-L6) | E. + expansion + rerank (bge-reranker-base) | G. A with 4 per tier (12 chunks): budget-only control | F. D with 4 per tier (12 chunks) = hybrid_stratified_rerank |
|---|---|---|---|---|---|---|---|
| Context recall (all chunks in context) | 0.61 [0.48, 0.74] | 0.64 [0.52, 0.75] | 0.68 [0.57, 0.79] | 0.69 [0.57, 0.79] | 0.69 [0.57, 0.80] | 0.65 [0.53, 0.76] | 0.74 [0.64, 0.84] |
| Recall@5 | 0.58 [0.45, 0.70] | 0.57 [0.45, 0.70] | 0.57 [0.45, 0.69] | 0.62 [0.49, 0.73] | 0.57 [0.43, 0.70] | 0.58 [0.45, 0.70] | 0.62 [0.49, 0.73] |
| Any-gold hit | 0.83 [0.69, 0.94] | 0.89 [0.77, 0.97] | 0.97 [0.91, 1.00] | 0.91 [0.80, 1.00] | 0.89 [0.77, 0.97] | 0.89 [0.77, 0.97] | 0.94 [0.86, 1.00] |
| Binding gold hit | 0.65 [0.46, 0.85] | 0.78 [0.61, 0.95] | 0.74 [0.55, 0.91] | 0.83 [0.65, 0.96] | 0.87 [0.71, 1.00] | 0.65 [0.46, 0.85] | 0.91 [0.78, 1.00] |
| Binding coverage | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| MRR | 0.63 [0.50, 0.75] | 0.57 [0.44, 0.70] | 0.72 [0.60, 0.85] | 0.76 [0.63, 0.87] | 0.68 [0.53, 0.81] | 0.63 [0.51, 0.75] | 0.76 [0.63, 0.87] |
| Retrieval latency / query (CPU) | 0.08s | 0.08s | 1.33s | 1.39s | 9.32s | 0.08s | 1.34s |

**Paired difference vs A** (same questions, paired bootstrap, 4,000 resamples):

| Variant | Δ context recall [95% CI] | P(Δ>0) | Δ binding gold hit [95% CI] |
|---|---|---|---|
| B. + query expansion | +0.03 [-0.04, +0.10] | 0.78 | +0.13 [-0.09, +0.35] |
| C. + rerank (MiniLM-L6) | +0.08 [+0.01, +0.16] | 0.99 | +0.09 [-0.09, +0.26] |
| D. + expansion + rerank (MiniLM-L6) | +0.08 [-0.04, +0.20] | 0.90 | +0.17 [-0.04, +0.39] |
| E. + expansion + rerank (bge-reranker-base) | +0.08 [-0.02, +0.19] | 0.94 | +0.22 [+0.00, +0.43] |
| G. A with 4 per tier (12 chunks): budget-only control | +0.04 [+0.01, +0.08] | 0.99 | +0.00 [+0.00, +0.00] |
| F. D with 4 per tier (12 chunks) = hybrid_stratified_rerank | +0.13 [+0.04, +0.23] | 1.00 | +0.26 [+0.04, +0.48] |

**Context recall by question type:**

| Type | A. hybrid_stratified (before) | B. + query expansion | C. + rerank (MiniLM-L6) | D. + expansion + rerank (MiniLM-L6) | E. + expansion + rerank (bge-reranker-base) | G. A with 4 per tier (12 chunks): budget-only control | F. D with 4 per tier (12 chunks) = hybrid_stratified_rerank |
|---|---|---|---|---|---|---|---|
| factual (n=13) | 0.88 | 0.88 | 0.88 | 0.81 | 0.85 | 0.88 | 0.88 |
| split (n=14) | 0.43 | 0.51 | 0.55 | 0.61 | 0.63 | 0.48 | 0.67 |
| cross_doc (n=8) | 0.47 | 0.46 | 0.59 | 0.62 | 0.54 | 0.55 | 0.62 |

Caveats: n is small; the query-expansion glossary was written after inspecting failures on these same draft questions (look-ahead risk) - confirm on the expert gold set before adopting.
