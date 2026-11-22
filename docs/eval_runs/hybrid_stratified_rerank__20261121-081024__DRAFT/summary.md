# Eval: hybrid_stratified_rerank  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `stratified`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: full; started 20261122-083646

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.618 [0.49, 0.73] | 35 |
| context_recall | 0.740 [0.63, 0.83] | 35 |
| any_gold_hit | 0.943 [0.85, 1.00] | 35 |
| mrr | 0.759 [0.63, 0.87] | 35 |
| binding_coverage | 1.000 [1.00, 1.00] | 23 |
| binding_gold_hit | 0.913 [0.79, 1.00] | 23 |
| faithfulness | 0.970 [0.93, 1.00] | 35 |
| answer_correctness | 0.887 [0.82, 0.94] | 40 |
| citation_validity | 1.000 [1.00, 1.00] | 36 |
| authority_label_accuracy | 1.000 [1.00, 1.00] | 36 |
| modality_error_rate | 0.000 [0.00, 0.00] | 36 |
| raw_citation_validity | 1.000 [1.00, 1.00] | 36 |
| raw_authority_label_accuracy | 0.989 [0.96, 1.00] | 36 |
| raw_modality_error_rate | 0.000 [0.00, 0.00] | 36 |
| tier_recall | 0.990 [0.97, 1.00] | 35 |
| fallback_rate | 0.000 [0.00, 0.00] | 40 |
| repair_rate | 0.025 [0.00, 0.07] | 40 |
| gate_abstain_rate | 0.100 [0.03, 0.20] | 40 |
| abstention_precision | 1.000 [1.00, 1.00] | 40 |
| abstention_recall | 0.800 [0.33, 1.00] | 40 |
| latency_p50_s | 37.050 | 36 |
| latency_p95_s | 41.551 | 36 |
| mean_input_tokens | 3820.425 |  |
| mean_output_tokens | 371.600 |  |
| mean_cost_usd | 0.000 |  |

n=40: differences smaller than the CI widths are noise.
