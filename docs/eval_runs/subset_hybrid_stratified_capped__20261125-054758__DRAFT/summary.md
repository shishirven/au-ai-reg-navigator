# Eval: hybrid_stratified_capped  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=6, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `stratified`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: full; started 20261125-054758

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.767 [0.50, 1.00] | 5 |
| context_recall | 0.767 [0.50, 1.00] | 5 |
| any_gold_hit | 1.000 [1.00, 1.00] | 5 |
| mrr | 0.850 [0.55, 1.00] | 5 |
| faithfulness | 1.000 [1.00, 1.00] | 5 |
| answer_correctness | 1.000 [1.00, 1.00] | 6 |
| citation_validity | 1.000 [1.00, 1.00] | 5 |
| authority_label_accuracy | 1.000 [1.00, 1.00] | 5 |
| modality_error_rate | 0.000 [0.00, 0.00] | 5 |
| raw_citation_validity | 1.000 [1.00, 1.00] | 5 |
| raw_authority_label_accuracy | 1.000 [1.00, 1.00] | 5 |
| raw_modality_error_rate | 0.000 [0.00, 0.00] | 5 |
| tier_recall | 1.000 [1.00, 1.00] | 5 |
| fallback_rate | 0.000 [0.00, 0.00] | 6 |
| repair_rate | 0.000 [0.00, 0.00] | 6 |
| gate_abstain_rate | 0.167 [0.00, 0.50] | 6 |
| abstention_precision | 1.000 [1.00, 1.00] | 6 |
| abstention_recall | 1.000 [1.00, 1.00] | 6 |
| latency_p50_s | 85.752 | 5 |
| latency_p95_s | 93.441 | 5 |
| mean_input_tokens | 7353.667 |  |
| mean_output_tokens | 495.333 |  |
| mean_cost_usd | 0.000 |  |

n=6: differences smaller than the CI widths are noise.
