# Eval: hybrid_pooled  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `hybrid`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: retrieval-only; started 20261119-052239

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.545 [0.40, 0.68] | 35 |
| mrr | 0.767 [0.63, 0.88] | 35 |
| binding_coverage | 0.609 [0.40, 0.80] | 23 |
| binding_gold_hit | 0.478 [0.26, 0.68] | 23 |

n=40: differences smaller than the CI widths are noise.
