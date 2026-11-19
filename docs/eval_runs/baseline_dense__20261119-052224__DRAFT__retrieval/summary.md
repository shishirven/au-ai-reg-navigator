# Eval: baseline_dense  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `dense`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: retrieval-only; started 20261119-052224

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.524 [0.40, 0.65] | 35 |
| mrr | 0.700 [0.56, 0.83] | 35 |
| binding_coverage | 0.478 [0.27, 0.68] | 23 |
| binding_gold_hit | 0.435 [0.23, 0.65] | 23 |

n=40: differences smaller than the CI widths are noise.
