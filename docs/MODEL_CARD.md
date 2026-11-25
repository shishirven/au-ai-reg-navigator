# Model card: AU AI Regulation Navigator

| | |
|---|---|
| System | Retrieval-augmented Q&A and a model-use checklist over Australian AI and financial regulation, for data and analytics teams |
| Version | prompt `v3`, index `idx-1174b9fc0ac3` (see `chroma/index_manifest_*.json`) |
| Owner | Shishir (portfolio project) |
| Status | **Demonstration / research prototype.** Not validated for production use. |
| Last reviewed | November 2026 |

## Purpose

Help **data leads, data scientists, ML engineers, actuaries and analytics teams** at Australian
banks and insurers work out which regulatory requirements apply to the models and AI they build or
buy, before they take the work to their risk, compliance and privacy partners (scope decision
D-051). Two modes:

* **Ask**: a question about AI or model use, answered with every statement **cited** and
  **labelled by legal force**:
  * **Mandatory**: binding prudential standards (APRA CPS 230, CPS 234, CPS 220)
  * **Regulator expects**: regulator guidance and letters (APRA CPG 230, CPG 235, APRA AI letter,
    OAIC guidance)
  * **Recommended**: voluntary government guidance (National AI Centre AI6)
* **Model-use check**: a short form about one model (personal information? decisions about
  people? vendor? offshore? critical operation?) produces a checklist grouped by lifecycle stage.
  Each item quotes its source paragraph and shows the evidence teams typically produce and who
  usually signs off. No language model is used in this mode (D-053).

Its distinguishing behaviour is surfacing **technology-neutral binding obligations** (for example,
CPS 230 service-provider requirements for an "AI vendor") that keyword- or similarity-based tools
miss because the standards never mention AI.

## Intended users and uses

| user | typical use |
|---|---|
| Data scientist / ML engineer | "We want to use an LLM API on customer emails: what applies?" Run a model-use check before the design review. |
| Actuary | Pricing or underwriting model: privacy disclosure of automated decisions (from 10 Dec 2026), validation and monitoring expectations, vendor rules for the ML platform. |
| Analytics / BI lead | Propensity and segmentation models driving offers: personal information use, fairness testing, model inventory. |
| Data / AI lead | A consistent first-pass checklist across the team's portfolio, exported as CSV into the risk assessment. |

Secondary users: risk partners, model validators and internal audit, to see which paragraphs a
team has considered and trace each to its source.

**Workflow.** Describe the use case → checklist by lifecycle stage → the team marks each item met /
not met / not applicable with evidence (CSV) → review and sign-off by risk, compliance and privacy
→ attach to the risk assessment or model inventory entry. The tool never concludes that a use case
is compliant.

## Out-of-scope uses

* **Legal advice** or determinations of whether an entity is compliant or in breach.
* Sole basis for any regulatory, credit, underwriting, claims or HR decision.
* **Superannuation trustees** (SPS standards not in the library) and organisations that are not
  APRA-regulated; the prudential items assume an APRA-regulated bank or insurer (D-051).
* Questions about documents not in the library: other jurisdictions (EU AI Act, GDPR), FAR, CPS 510,
  ASIC guidance, the Corporations Act, insurance and consumer-credit law, anti-discrimination law,
  actuarial professional standards, and the Privacy Act text itself (staged, not yet live). Answers
  and checklists name these as **not covered** so users check them separately (D-054).
* Confidential product details in the **public demo**: questions there are logged for tracing.
  Real use means self-hosting with the organisation's approved model and tracing off.
* Monitoring regulatory change: the library is a fixed snapshot (see versions below).

## System components

| component | default |
|---|---|
| Embedding | `BAAI/bge-small-en-v1.5` (local, CPU) |
| Keyword retrieval | BM25 (Okapi) |
| Fusion / routing | reciprocal rank fusion (k = 60), per-tier quota of 3 chunks |
| Generator | `qwen/qwen3.8-27b` on Groq (temperature 0, seed 42, reasoning off). On a laptop, **automatic local fallback** to Ollama `qwen3:4b` when Groq is rate-limited or down, clearly flagged (D-041). The public demo falls back to free-tier Gemini `gemini-3.8-flash` instead, then abstains if that also fails (D-050). Reported eval numbers are Groq only and stay **provisional**. Alternative for local experiments: Claude via Anthropic API |
| Judge (evaluation only) | `openai/gpt-oss-120b` on Groq: a different model family from the generator |
| Controls | scope gate → validator → claim-level repair → one retry → safe abstention; disclaimer on every answer |

## Corpus and versions

12 documents, 604 chunks (index `idx-1174b9fc0ac3`, built 2026-11-25, ingest code `384b7a7487cc`): one per numbered paragraph or heading section, plus 82 footnote chunks and table rows kept since the table/footnote parser fix (F-13, D-059).
Superseded documents are indexed but **excluded from retrieval by default**.

| doc id | tier | status | chunks | sha256 (12) |
|---|---|---|---|---|
| `apra_cps230_2026` | binding | current | 61 | `182a241027c4` |
| `apra_cps230_2023` | binding | superseded | 59 | `f296a7e0bead` |
| `apra_cps220` | binding | current | 58 | `67ba3f292eb1` |
| `apra_cps234` | binding | current | 34 | `d86abbb56970` |
| `apra_cpg230_2026` | expectation | current | 70 | `0927f6eea402` |
| `apra_cpg235` | expectation | current | 68 | `0013cf70eb7b` |
| `apra_ai_letter_2026` | expectation | current | 11 | `785b8d524c18` |
| `oaic_app1_adm_2026` | expectation | current | 19 | `8c0249654e0c` |
| `oaic_ai_products_2025` | expectation | current | 68 | `700060790e41` |
| `naic_ai6_foundations` | voluntary | current | 12 | `f2e0d41257fa` |
| `disr_vaiss_2024` | voluntary | superseded | 49 | `8fce1c5a9025` |
| `disr_ai_ethics_2019` | voluntary | superseded | 13 | `a912cafc8c02` |

Source URLs, effective dates and provenance: `data/sources.yaml` and `data/raw/manifest.csv`.
Six sources are web pages saved as Markdown (no official PDF was available, or download was blocked).

## Performance

See `docs/results.md` (generated by `make compare`) and `docs/VALIDATION_REPORT.md`. Headline
metrics: binding-source coverage, faithfulness, citation validity, authority-label accuracy,
modality error rate and abstention precision/recall, each with 95% bootstrap CIs.
**n = 30–40 questions: small differences are not statistically meaningful.**

## Limitations and known risks

1. **Tier is a property of the document, not the obligation.** The OAIC APP 1.7–1.9 fact sheet is
   labelled "Regulator expects" although it explains a *binding* Privacy Act obligation (from
   10 Dec 2026). Claims citing such guidance carry a "⚖️ Explains binding law" note (D-043), but the
   obligation itself is not shown under "Mandatory" until the statutory text is added to the corpus.
   Never read "Regulator expects" as "optional".
2. **Corpus coverage**: no Privacy Act text, ASIC guidance, SPS standards (super-specific risk
   management), APRA capital standards or proposed mandatory AI guardrails.
3. **Point-in-time snapshot**: documents retrieved November 2026; no automated change detection
   against the Federal Register of Legislation.
4. **Parsing heuristics** (headers, footnotes, headings) were tuned on these PDFs; new layouts
   may mis-parse. Paragraph ids depend on parsing.
5. **Small evaluation set** written by the developer; the judge is itself an LLM (calibration
   against human labels is reported separately).
6. **Model dependence**: a smaller local model (Qwen3-4B) makes more validation errors, needs
   the repair path more often and gives less complete answers. When the app falls back to it, the
   answer is flagged on screen ("Local model" badge and banner). Evaluation results describe the
   Groq model only.
7. **Scope gate is heuristic** (keyword list of jurisdictions/instrument codes, similarity floor)
   and was designed after seeing the draft questions.
8. **Modality tagging is regex-based** and chunk-level: a chunk containing both "must" and "should"
   is tagged "must".

## Ethical and regulatory considerations

* Every answer carries a "not legal advice" disclaimer and cites its sources, so users can verify it.
* No personal information is collected; questions are traced (Langfuse) for quality monitoring.
* Third-party model providers (Groq, optionally Anthropic) receive the question and retrieved
  public-document text only.
