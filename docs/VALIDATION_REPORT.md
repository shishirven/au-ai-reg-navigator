# Model Validation Report: AU AI Regulation Navigator

| | |
|---|---|
| Model / system | AU AI Regulation Navigator (tier-aware RAG), prompt `v3` |
| Version under review | index `idx-2185d086e9c4` · config `hybrid_stratified` · generator `groq/qwen/qwen3.8-27b` · judge `groq/openai/gpt-oss-120b` |
| Validation type | Initial validation (pre-release) |
| Model tier (proposed) | Low–moderate: decision-*support* tool, human in the loop, no automated decisions |
| Validator | Self-assessment in Line-2 format (portfolio project). **Not independent**; see §9 |
| Date | November 2026 |
| Overall conclusion | **Fit for purpose as a demonstration / research aid. Not approved for production** pending the conditions in §10. |

---

## 1. Scope

**In scope:** the end-to-end question-answering pipeline: source registry and ingestion
(parsing, chunking, modality tagging, indexing, versioning), retrieval (three configurations),
generation (prompting, structured output, scope gate, validator, claim repair, fallback),
observability, the evaluation harness itself, and the release gate.

**Out of scope:** legal correctness of the source documents; the Streamlit UI beyond functional
smoke tests; third-party model internals (Groq-hosted Qwen and gpt-oss); infrastructure security
of a production deployment.

**Intended use under review:** surfacing and labelling, by legal force, what Australian regulatory
documents say about AI-related questions, for compliance and risk staff who then read the cited
source. See `docs/MODEL_CARD.md`.

## 2. System description (summary)

Twelve documents (3 binding APRA standards current + 1 superseded; 5 regulator-expectation
documents; 1 voluntary current + 2 superseded) are parsed into 522 paragraph-level chunks carrying
tier, sector applicability, status and modality metadata. A question is answered by:

1. hybrid retrieval (BGE dense + BM25, reciprocal-rank fusion) run **separately per tier** with a
   quota of 3 chunks per tier;
2. a scope gate (similarity floor, out-of-corpus jurisdiction or instrument);
3. an LLM producing JSON claims in *mandatory / regulator_expects / recommended* sections, each with a
   citation;
4. a deterministic validator (citations ⊂ retrieved, section = cited tier, no "must" on "should"
   sources), claim-level repair, one LLM retry and a safe-abstention fallback.

Architecture: `docs/ARCHITECTURE.md`. Design decisions and their rationale: `DECISIONS.md` (D-001 to D-040).

## 3. Conceptual soundness

| aspect | assessment |
|---|---|
| **Problem framing** | Sound. The failure mode is real and is reproduced: technology-neutral binding standards are under-retrieved by similarity search for AI-worded questions (§5.1). |
| **Tier stratification** | Appropriate remedy: it guarantees representation of each legal tier in the context window, at the cost of a fixed context budget per tier. Trade-off: lower MRR (interleaving) and possible irrelevant binding chunks when no binding text applies; the validator and judge measure the consequences. |
| **Authority labelling by source tier** | Sound and auditable: the label is derived from document metadata, not from model judgement, and is enforced by the validator. **Limitation:** tier is a property of the document, not the obligation (OAIC fact sheet explains a binding Privacy Act duty but is labelled *Regulator expects*). See Finding F-03. |
| **Modality controls** | Regex modality tagging is simple, transparent and unit-tested (19 cases incl. negations). Chunk-level granularity is coarse (Finding F-07). |
| **Abstention design** | Two layers: a pre-generation scope gate plus model instruction. Gate heuristics were designed after viewing the draft questions, a look-ahead risk (Finding F-02). |
| **Determinism & versioning** | Strong: content-addressed `index_version` covering sources, metadata, chunking, embedding and ingest code; fixed seeds; temperature 0; every answer and eval run carries config and index version. Cross-platform determinism defect found and fixed (F-09). |

## 4. Data

| item | evidence |
|---|---|
| Provenance | `data/raw/manifest.csv` (issuer, version, official URL, retrieval notes) and `data/sources.yaml` (sha256 per file, written by ingest). Six sources are official web pages saved as Markdown; their text was extracted from the official URL because direct download was blocked. **Residual risk:** those transcriptions are not byte-verifiable against an official PDF. |
| Parsing quality | Inspected on all 6 PDFs (running headers, footnotes, two-column layout, quote boxes). One defect found during gold labelling (CPS 220 paragraph-marker order, D-037) and fixed with a regression test. |
| Coverage gaps | No Privacy Act/APP text, ASIC guidance, SPS (superannuation) risk standards, APRA capital standards, or proposed mandatory AI guardrails. |
| Currency | Snapshot retrieved 18 Nov 2026. No automated change detection against source registers. |

## 5. Testing performed and results

Test layers are described in `docs/TEST_PLAN.md`.

| layer | result |
|---|---|
| Unit (157) + integration (10) | **All pass** (167), hermetic (no network/keys). Coverage ≈ 82% of `regnav/`. |
| Retrieval regression gate (CI, fixtures, real BGE) | **Pass** for `hybrid_stratified` (recall@5 1.00, MRR 1.00, binding coverage 1.00). Control: the dense baseline config **fails** the gate (binding coverage 0.75), confirming the gate discriminates. |
| Adversarial (live LLM) | **4 / 5 pass** (prompt injection, out-of-scope abstention, legal-advice request, voluntary-only topic). The 5th (not-yet-in-force date) did not execute: it hit the provider's rate limit while a full eval was running (infrastructure, not model behaviour); re-run scheduled. The same behaviour *was* observed in the CLI demo (answer states 10 Dec 2026 commencement). |
| Full evaluation | §5.1–5.3 below. **Provisional:** 40 developer-written DRAFT questions. |

### 5.1 Retrieval: the core claim (all three configurations, 40 draft questions)

| metric | dense pooled | hybrid pooled | **hybrid stratified** |
|---|---|---|---|
| Recall@5 | 0.52 [0.40, 0.65] | 0.55 [0.40, 0.68] | 0.58 [0.44, 0.70] |
| MRR | 0.70 [0.56, 0.83] | 0.77 [0.63, 0.88] | 0.63 [0.49, 0.75] |
| **Binding-source coverage** (n = 23) | **0.48** [0.27, 0.68] | **0.61** [0.40, 0.80] | **1.00** [1.00, 1.00] |
| Binding gold chunk retrieved (n = 23) | 0.43 [0.23, 0.65] | 0.48 [0.26, 0.68] | 0.65 [0.44, 0.85] |

*Interpretation.* Binding coverage is the only metric whose intervals separate: stratification
removes the failure mode in which binding obligations never reach the model. Recall@5 differences
are within noise. MRR is lower for stratified **by design** (per-tier interleaving).

### 5.2 Generation: hybrid stratified (full eval, 40 draft questions)

| metric | value [95% CI] | threshold | status |
|---|---|---|---|
| Faithfulness (judge) | 0.966 [0.93, 0.99] | ≥ 0.85 | pass |
| Answer correctness (judge) | 0.769 [0.66, 0.86] | n/a (monitored) | see F-01 |
| Citation validity (final) | 1.000 | ≥ 0.98 | pass |
| Authority-label accuracy (final) | 1.000 | ≥ 0.95 | pass |
| Modality error rate (final) | 0.000 | ≤ 0.02 | pass |
| Raw authority-label accuracy (pre-validation) | 0.986 [0.96, 1.00] | n/a (monitored) | 1 misfiled claim, repaired |
| Raw modality error rate | 0.000 | n/a (monitored) | |
| Abstention precision / recall | 1.00 / 0.80 [0.33, 1.00] | recall ≥ 0.80 | pass (borderline; n = 5) |
| Safe-fallback / repair / gate rate | 0.00 / 0.025 / 0.10 | fallback ≤ 0.10 | pass |
| Latency p50 / p95 | 28 s / 59 s | n/a | dominated by free-tier rate-limit waits; raw generation 1–7 s |

**Comparison with the pooled baselines (generation): pending.** The two baseline full runs were
interrupted by the provider's daily token quota and are scheduled to resume (D-038, D-039). This
section will be updated with `docs/results.md`.

### 5.3 Outcome analysis (qualitative review of low-scoring answers)

Twelve of 35 answered questions scored correctness ≤ 0.5. The judge's rationales were reviewed:
in 11 of the 12, **every claim was supported by its source** (faithful) but the answer omitted the key
obligation, e.g. the 20-business-day APRA notification (D03), CPS 234 third-party control
assessment (D06), or that AI6 is voluntary (D34). In each case the omitted paragraph was **not
retrieved**. The limiting factor is retrieval *precision within tier*, not generation. The
remaining low score (D39, proposed mandatory guardrails) is an abstention miss.

## 6. Judge calibration

The LLM judge (gpt-oss-120b) is a different model family from the generator (Qwen), to limit
self-preference bias. Ten judged answers have been exported to `data/eval/judge_calibration.csv`
for blind human labelling (correctness 1–5; all-claims-supported y/n). **Cohen's κ: pending human
labels.** Running `make judge-calibration` again computes quadratic-weighted κ (correctness),
pass/fail κ, and κ for faithfulness, and logs them to MLflow. **Until κ ≥ 0.6 is shown, judge-based
metrics should be treated as indicative only.**

## 7. Findings

| ID | severity | finding | status / remediation |
|---|---|---|---|
| F-01 | **Medium** | Answers are faithful but incomplete (correctness 0.77); the key paragraph is often not retrieved (recall@5 0.58). Diagnosis: 97% of gold paragraphs are in the top-40 candidate pool, so it is a *ranking* gap, concentrated in split/cross-document questions (AI wording vs tech-neutral text). | **Partially remediated** by the opt-in config `hybrid_stratified_rerank` (D-042): query expansion + cross-encoder re-ranking, 4 per tier. Context recall 0.61 → 0.74 (paired Δ +0.13 [+0.04, +0.23]); binding gold hit 0.65 → 0.91 (Δ +0.26 [+0.04, +0.48]); a budget-only control shows the gain comes from re-ranking/expansion, not the larger context (`docs/retrieval_ablation.md`). Impact on answer correctness: pending the scheduled full eval. Glossary look-ahead risk: confirm on the gold set. |
| F-02 | **Medium** | Scope-gate rules were designed after viewing the draft questions (look-ahead bias); abstention recall based on n = 5. | Open. Validate on the expert-written gold set, with ≥ 8 unanswerable questions not seen during design. |
| F-03 | **High** (raised from Medium after user review) | Tier label reflects the document, not the obligation. Observed in use: "When does the APP 1.7–1.9 ADM transparency obligation commence?" was answered under *Regulator expects · guidance – not itself enforceable*, although APP 1.7–1.9 is binding Privacy Act law from 10 Dec 2026. This is exactly the authority mislabelling the system is designed to prevent. | **Mitigated** (D-043): display-only authority notes flag claims citing guidance that explains binding law ("⚖️ Explains binding law: Privacy Act 1988 – APP 1.7–1.9, in force from 2026-12-10"), and misleading subtitle removed. **Open:** add the APP 1.7–1.9 statutory text as a binding source so the obligation appears under *Mandatory*; re-index and re-evaluate after the in-flight eval completes; add gold questions where guidance restates law. |
| F-04 | Low | One unanswerable question (proposed mandatory AI guardrails) answered from related documents instead of abstaining. | Open. Add "proposed/draft" detection to the gate and an explicit "not yet law" rule; add a *Proposed* tier when such documents are added. |
| F-05 | Low (fixed) | An eval-infrastructure defect recorded LLM quota failures as abstentions, which would have biased the baseline's scores downward. | **Fixed** (D-039): outages abort and are resumed, never recorded. Affected rows were removed. |
| F-06 | Low (fixed) | CPS 220 paragraph markers attached to the wrong paragraphs (PDF reading order). | **Fixed** (D-037) with a regression test; found during gold labelling, i.e. the labelling process worked as a control. |
| F-07 | Low | Modality is tagged per chunk (strongest wins), so a "should" sentence inside a "must" chunk could be stated as mandatory without a validator error. | Open. Sentence-level modality or claim-to-sentence alignment. |
| F-08 | Low | Evaluation questions and reference answers were written by the developer, a validation-independence issue. | Open. Expert-written gold set (user) required before release (§10). |
| F-09 | Low (fixed) | Index version differed between Windows and Linux checkouts (line endings). | **Fixed** (D-040), `.gitattributes`. |
| F-10 | Info | Latency and throughput on the free inference tier are bounded by rate limits (200k tokens/day/model). | Production would need a paid tier or self-hosting; capacity test required. |

## 8. Limitations

* Small evaluation set (n = 40 drafts; 23 with binding gold; 5 unanswerable); confidence intervals are wide.
* Single run per configuration; generator determinism (temperature 0, seed) is good but not
  guaranteed by the hosted provider; run-to-run variance not yet measured.
* LLM-as-judge without completed calibration.
* English-language, Australian-federal scope; point-in-time corpus.

## 9. Independence and governance of this validation

This report was prepared by the system's developer using an independent-validation **template**.
In a regulated entity it would be performed by Line 2 (model risk), with independent
re-performance of the evaluation on a held-out question set, review of the judge calibration, and
challenge of the conceptual design. Everything needed to reproduce it is versioned: code, configs,
`uv.lock`, source hashes, per-question outputs (`docs/eval_runs/`) and MLflow runs.

## 10. Conclusion and conditions for production use

**Approved** as a demonstration and research aid. **Not approved for production** until:

1. an expert-reviewed gold set (`data/eval/questions.jsonl`, ≥ 30 questions incl. ≥ 8 unanswerable)
   passes `make release-check` (no `--allow-draft`);
2. judge calibration κ ≥ 0.6 against human labels;
3. the pooled-baseline generation comparison is complete (scheduled);
4. F-01 and F-03 have remediation plans with owners.

Current release-gate output (draft evidence, `--allow-draft`): **APPROVED** on all thresholds.
Without `--allow-draft` the gate **BLOCKS** (no gold-set run), as designed.

## 11. Ongoing monitoring and triggers

| trigger | action |
|---|---|
| Any source **sha256** change, `sources.yaml` metadata change, chunking/embedding change or ingest-code change (⇒ new `index_version`) | Full re-evaluation; release gate blocks until done (D-036) |
| Faithfulness < 0.85, citation validity < 0.98, modality error rate > 0.02, authority-label accuracy < 0.95, binding coverage < 0.90, abstention recall < 0.80, fallback rate > 0.10 | Block release; investigate (`configs/release_thresholds.yaml`) |
| Generator or judge model/version change | Full re-evaluation + judge recalibration |
| Production telemetry (Langfuse): fallback rate, repair rate, gate-abstain rate, p95 latency drift | Weekly review; investigate step changes |
| New regulatory publication (APRA, OAIC, NAIC) | Add to corpus → new index version → full re-eval |
| Retrieval regression gate fails in CI | Merge blocked |

## 12. Mapping of this tool's own controls to the APRA AI letter (April 2026)

The APRA letter sets expectations for entities' use of AI. As an AI system, this tool applies
the same expectations to itself:

| APRA letter area | APRA expectation (summary) | control in this system |
|---|---|---|
| **Information security** | AI-specific threats (prompt injection, data leakage, insecure integrations); security testing for AI | Source text delimited and escaped as data; injection adversarial test; secrets only via `.env`/proxy, excluded from images and logs; non-root container; no PII collected |
| **Governance** | Ownership and accountability across the AI lifecycle; inventory; human involvement for high-risk decisions | Model card (owner, purpose, out-of-scope uses); decision log; every answer is decision *support* with citations and a "not legal advice" disclaimer; abstention instead of guessing |
| **Supplier risk** | Visibility of the AI supply chain; transparency, auditability; concentration risk and credible substitution | Provider-agnostic LLM interface (Groq, Ollama, Anthropic) switchable by config and re-validated by the same eval; open-weight models; embedding model pinned and baked into the image; dependency lockfile |
| **Change management & assurance** | Change control for AI; continuous validation and monitoring rather than point-in-time; capable second/third line | Content-addressed index versions; release gate tied to index version and thresholds; CI regression gate; resumable, versioned eval runs in MLflow; Langfuse tracing of every query; this validation report and its monitoring triggers |
