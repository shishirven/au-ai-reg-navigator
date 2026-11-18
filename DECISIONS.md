# Decisions log

Choices made without asking, so they can be reviewed. Newest last.

| ID | Decision | Why / alternatives |
|----|----------|--------------------|
| D-001 | **Python 3.12**, `requires-python >=3.11,<3.13`. | Within the brief's 3.11+; 3.12 has wheels for every dependency (torch, chromadb, pymupdf). |
| D-002 | **CPU-only torch from the PyTorch CPU index for every platform** (`[tool.uv.sources]`), lock restricted to linux x86_64/aarch64 + macOS. | The brief asks for CPU torch in Docker; using it everywhere keeps one `uv.lock`, keeps CI fast and avoids multi-GB CUDA wheels. |
| D-003 | **Generator `claude-opus-5-5`, judge `claude-sonnet-5-5`**, both set in `configs/*.yaml`, not in code. | The judge is a different model from the generator, as the brief asks, to reduce self-preference bias. Prices are in the config for cost tracking. |
| D-004 | **No `temperature: 0`.** The field exists in config but defaults to `null` and is only sent when set. | Current Claude models reject sampling parameters (API version 2026-10-21+). For determinism we rely on: a fixed prompt, JSON-schema structured output, the effort setting, fixed seeds for everything local, a pinned `uv.lock` and versioned indexes. Run-to-run LLM variance is measured, not assumed away (see VALIDATION_REPORT). |
| D-005 | **Structured output through `output_config.format` (JSON schema)**, then our own post-hoc validator (`generate/validate.py`). | The schema guarantees parseable JSON. Semantic rules (citations in the retrieved set, tier/section consistency, modality) need our own code either way, and that code can be unit-tested with a stub LLM. |
| D-006 | **Two embedding backends:** `sentence_transformers` (BGE-small, the default for all real configs) and a deterministic `hashing` bag-of-words backend. | The hashing backend lets unit and integration tests run hermetically (no model download, no network). The CI retrieval regression gate uses the **real** BGE model, with the model cached between runs. |
| D-007 | **Fixture corpus stored as `.txt` and rendered to PDF at test time** (`regnav/fixtures.py`). | The fixtures stay readable and diff-able in git, while the real PyMuPDF parsing path (including font-size heading detection) is still exercised end-to-end. |
| D-008 | `data/sources.yaml`: `url` and `effective_from` left blank (marked `TODO(user)`). A `file` field maps each entry to its PDF in `data/raw/`. | Per the brief: don't guess. The OAIC guidance title also needs confirming. |
| D-009 | **OAIC ADM guidance and the APRA AI letter are both tier `expectation`**; the OAIC guidance has `applies_to: [any_business]`. | The guidance explains a *binding* Privacy Act obligation, but the document itself is regulator guidance. Classifying the Privacy Act itself as binding would need the Act in the corpus (listed as a next step). |
| D-010 | **Sector filter semantics:** a document is in scope for sector *S* if `applies_to` contains *S* **or** `any_business`. | Voluntary, economy-wide guidance applies to banks too; excluding it would remove the "Recommended" tier for every sector. |
| D-011 | GitHub repo: this session cannot create new GitHub repositories, so the code is built locally and pushed once the user creates an empty `au-ai-reg-navigator` repo. | Tooling constraint; see the Phase 1 checkpoint. |
