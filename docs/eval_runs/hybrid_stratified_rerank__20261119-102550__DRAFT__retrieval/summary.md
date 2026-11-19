# Eval: hybrid_stratified_rerank  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `stratified`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: retrieval-only; started 20261119-102550

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.618 [0.49, 0.73] | 35 |
| context_recall | 0.740 [0.63, 0.83] | 35 |
| any_gold_hit | 0.943 [0.85, 1.00] | 35 |
| mrr | 0.759 [0.63, 0.87] | 35 |
| binding_coverage | 1.000 [1.00, 1.00] | 23 |
| binding_gold_hit | 0.913 [0.79, 1.00] | 23 |

n=40: differences smaller than the CI widths are noise.
