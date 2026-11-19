# Eval: hybrid_stratified  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `stratified`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: retrieval-only; started 20261119-052248

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.576 [0.44, 0.70] | 35 |
| mrr | 0.626 [0.49, 0.75] | 35 |
| binding_coverage | 1.000 [1.00, 1.00] | 23 |
| binding_gold_hit | 0.652 [0.44, 0.85] | 23 |

n=40: differences smaller than the CI widths are noise.
