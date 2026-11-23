# Eval: hybrid_stratified_capped  (DRAFT QUESTIONS - provisional)

- questions: `data/eval/questions_draft.jsonl` (n=40, sha256 f062a2c351ee)
- index_version: `idx-2185d086e9c4`; retrieval mode: `stratified`
- generator: `groq/qwen/qwen3.8-27b`; judge: `groq/openai/gpt-oss-120b`
- mode: full; started 20261123-042705

| metric | value [95% bootstrap CI] | n |
|---|---|---|
| recall_at_5 | 0.618 [0.49, 0.73] | 35 |
| context_recall | 0.748 [0.65, 0.84] | 35 |
| any_gold_hit | 0.971 [0.91, 1.00] | 35 |
| mrr | 0.761 [0.63, 0.88] | 35 |
| binding_coverage | 1.000 [1.00, 1.00] | 23 |
| binding_gold_hit | 0.913 [0.78, 1.00] | 23 |
| faithfulness | 0.965 [0.93, 0.99] | 35 |
| answer_correctness | 0.844 [0.75, 0.93] | 40 |
| citation_validity | 1.000 [1.00, 1.00] | 36 |
| authority_label_accuracy | 1.000 [1.00, 1.00] | 36 |
| modality_error_rate | 0.000 [0.00, 0.00] | 36 |
| raw_citation_validity | 1.000 [1.00, 1.00] | 36 |
| raw_authority_label_accuracy | 1.000 [1.00, 1.00] | 36 |
| raw_modality_error_rate | 0.000 [0.00, 0.00] | 36 |
| tier_recall | 1.000 [1.00, 1.00] | 35 |
| fallback_rate | 0.000 [0.00, 0.00] | 40 |
| repair_rate | 0.000 [0.00, 0.00] | 40 |
| gate_abstain_rate | 0.100 [0.03, 0.20] | 40 |
| abstention_precision | 1.000 [1.00, 1.00] | 40 |
| abstention_recall | 0.800 [0.33, 1.00] | 40 |
| latency_p50_s | 35.890 | 36 |
| latency_p95_s | 41.962 | 36 |
| mean_input_tokens | 3820.200 |  |
| mean_output_tokens | 360.350 |  |
| mean_cost_usd | 0.000 |  |

n=40: differences smaller than the CI widths are noise.
