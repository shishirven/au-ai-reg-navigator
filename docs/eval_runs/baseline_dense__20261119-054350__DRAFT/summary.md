# Eval: baseline_dense  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `dense`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: full; started 20261120-073104

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.524 [0.40, 0.65] | 35 |
| context_recall | 0.595 [0.48, 0.70] | 35 |
| any_gold_hit | 0.914 [0.80, 1.00] | 35 |
| mrr | 0.700 [0.55, 0.83] | 35 |
| binding_coverage | 0.478 [0.27, 0.68] | 23 |
| binding_gold_hit | 0.435 [0.23, 0.64] | 23 |
| faithfulness | 1.000 [1.00, 1.00] | 35 |
| answer_correctness | 0.775 [0.67, 0.87] | 40 |
| citation_validity | 1.000 [1.00, 1.00] | 36 |
| authority_label_accuracy | 1.000 [1.00, 1.00] | 36 |
| modality_error_rate | 0.000 [0.00, 0.00] | 36 |
| raw_citation_validity | 1.000 [1.00, 1.00] | 36 |
| raw_authority_label_accuracy | 0.984 [0.96, 1.00] | 36 |
| raw_modality_error_rate | 0.000 [0.00, 0.00] | 36 |
| tier_recall | 0.805 [0.70, 0.90] | 35 |
| fallback_rate | 0.000 [0.00, 0.00] | 40 |
| repair_rate | 0.050 [0.00, 0.12] | 40 |
| gate_abstain_rate | 0.100 [0.03, 0.20] | 40 |
| abstention_precision | 1.000 [1.00, 1.00] | 40 |
| abstention_recall | 0.800 [0.33, 1.00] | 40 |
| latency_p50_s | 33.323 | 36 |
| latency_p95_s | 37.853 | 36 |
| mean_input_tokens | 3318.150 |  |
| mean_output_tokens | 274.575 |  |
| mean_cost_usd | 0.000 |  |

n=40: differences smaller than the CI widths are noise.
