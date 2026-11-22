# Eval: hybrid_pooled  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `hybrid`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: full; started 20261122-083642

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.545 [0.40, 0.68] | 35 |
| context_recall | 0.605 [0.48, 0.72] | 35 |
| any_gold_hit | 0.914 [0.81, 1.00] | 35 |
| mrr | 0.767 [0.63, 0.88] | 35 |
| binding_coverage | 0.609 [0.40, 0.80] | 23 |
| binding_gold_hit | 0.478 [0.26, 0.68] | 23 |
| faithfulness | 0.938 [0.86, 0.99] | 35 |
| answer_correctness | 0.762 [0.65, 0.86] | 40 |
| citation_validity | 1.000 [1.00, 1.00] | 36 |
| authority_label_accuracy | 1.000 [1.00, 1.00] | 36 |
| modality_error_rate | 0.000 [0.00, 0.00] | 36 |
| raw_citation_validity | 1.000 [1.00, 1.00] | 36 |
| raw_authority_label_accuracy | 0.994 [0.98, 1.00] | 36 |
| raw_modality_error_rate | 0.006 [0.00, 0.02] | 36 |
| tier_recall | 0.862 [0.78, 0.93] | 35 |
| fallback_rate | 0.000 [0.00, 0.00] | 40 |
| repair_rate | 0.025 [0.00, 0.07] | 40 |
| gate_abstain_rate | 0.100 [0.03, 0.20] | 40 |
| abstention_precision | 1.000 [1.00, 1.00] | 40 |
| abstention_recall | 0.800 [0.33, 1.00] | 40 |
| latency_p50_s | 33.939 | 36 |
| latency_p95_s | 39.116 | 36 |
| mean_input_tokens | 3340.625 |  |
| mean_output_tokens | 263.125 |  |
| mean_cost_usd | 0.000 |  |

n=40: differences smaller than the CI widths are noise.
