# Results

> **PROVISIONAL - scored on DRAFT questions** (`data/eval/questions_draft.jsonl`) that have not yet been reviewed by a domain expert. Re-run `make eval-all && make compare` after the gold set (`data/eval/questions.jsonl`) is written.

| Metric | `baseline_dense` | `hybrid_pooled` | `hybrid_stratified` | `hybrid_stratified_rerank` |
|---|---|---|---|---|
| ***Retrieval*** | | | | |
| Recall@5 | 0.524 [0.40, 0.65] | 0.545 [0.40, 0.68] | 0.576 [0.44, 0.70] | 0.618 [0.49, 0.73] |
| Context recall (all chunks given to the model) | - | - | - | 0.740 [0.63, 0.83] |
| Any gold chunk in context | - | - | - | 0.943 [0.85, 1.00] |
| MRR | 0.700 [0.56, 0.83] | 0.767 [0.63, 0.88] | 0.626 [0.49, 0.75] | 0.759 [0.63, 0.87] |
| **Binding-source coverage** | 0.478 [0.27, 0.68] | 0.609 [0.40, 0.80] | 1.000 [1.00, 1.00] | 1.000 [1.00, 1.00] |
| Binding gold chunk retrieved | 0.435 [0.23, 0.65] | 0.478 [0.26, 0.68] | 0.652 [0.44, 0.85] | 0.913 [0.79, 1.00] |
| ***Generation (LLM judge)*** | | | | |
| Faithfulness | - | - | 0.966 [0.93, 0.99] | - |
| Answer correctness | - | - | 0.769 [0.66, 0.86] | - |
| ***Generation (rule-based, final answer)*** | | | | |
| Citation validity | - | - | 1.000 [1.00, 1.00] | - |
| Authority-label accuracy | - | - | 1.000 [1.00, 1.00] | - |
| Modality error rate (lower is better) | - | - | 0.000 [0.00, 0.00] | - |
| Expected-tier recall | - | - | 1.000 [1.00, 1.00] | - |
| ***Model reliability (first raw attempt, before validation/repair)*** | | | | |
| Raw citation validity | - | - | 1.000 [1.00, 1.00] | - |
| Raw authority-label accuracy | - | - | 0.986 [0.96, 1.00] | - |
| Raw modality error rate | - | - | 0.000 [0.00, 0.00] | - |
| ***Abstention & safety net*** | | | | |
| Abstention precision | - | - | 1.000 [1.00, 1.00] | - |
| Abstention recall | - | - | 0.800 [0.33, 1.00] | - |
| Scope-gate abstentions | - | - | 0.100 [0.03, 0.20] | - |
| Claim-repair rate | - | - | 0.025 [0.00, 0.07] | - |
| Safe-fallback rate | - | - | 0.000 [0.00, 0.00] | - |
| ***System*** | | | | |
| Latency p50 (s) | - | - | 28.5 | - |
| Latency p95 (s) | - | - | 59.4 | - |
| Input tokens / query | - | - | 3055.8 | - |
| Output tokens / query | - | - | 373.4 | - |
| Cost / query (USD) | - | - | 0.0000 | - |

Values: mean [95% percentile-bootstrap CI over questions].

### Runs

| config | run | questions | n | index | generator / judge |
|---|---|---|---|---|---|
| `baseline_dense` | `baseline_dense__20261119-052224__DRAFT__retrieval` (retrieval-only) | `data/eval/questions_draft.jsonl` | 40 | `idx-2185d086e9c4` |  |
| `hybrid_pooled` | `hybrid_pooled__20261119-052239__DRAFT__retrieval` (retrieval-only) | `data/eval/questions_draft.jsonl` | 40 | `idx-2185d086e9c4` |  |
| `hybrid_stratified` | `hybrid_stratified__20261119-052448__DRAFT` (full) | `data/eval/questions_draft.jsonl` | 40 | `idx-2185d086e9c4` | groq/qwen/qwen3.8-27b |
| `hybrid_stratified_rerank` | `hybrid_stratified_rerank__20261119-102550__DRAFT__retrieval` (retrieval-only) | `data/eval/questions_draft.jsonl` | 40 | `idx-2185d086e9c4` | groq/qwen/qwen3.8-27b |

### How to read this

- **n is small (30-40 questions).** Differences smaller than the CI widths are noise; treat only non-overlapping intervals as evidence.
- **Binding-source coverage** = share of questions whose gold answer includes a binding standard where at least one binding chunk reached the generator. This is the metric the tier-stratified design is meant to move.
- Final-answer citation validity / authority labels are enforced by the validator (invalid answers are repaired or replaced by a safe abstention), so the *raw* rows are the honest measure of model reliability; the repair and fallback rates show how often the safety net was needed.
- Rule-based metrics are deterministic; judge metrics depend on the judge model (see judge calibration in VALIDATION_REPORT.md).
