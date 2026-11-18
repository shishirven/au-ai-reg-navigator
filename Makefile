# AU AI Regulation Navigator - developer entry points. Everything runs through uv.
CONFIG ?= configs/hybrid_stratified.yaml
Q ?= What do we need to do before engaging a third-party AI vendor?
SECTOR ?= bank
UV := uv run

.PHONY: help install lint format typecheck test test-unit test-integration test-adversarial \
        coverage regression-gate ingest ask eval eval-all compare judge-calibration \
        release-check chunks app docker-build up down clean

help:  ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install:  ## Create venv from uv.lock and install pre-commit hooks
	uv sync --frozen
	$(UV) pre-commit install

lint:  ## ruff lint + format check
	$(UV) ruff check .
	$(UV) ruff format --check .

format:  ## Auto-format
	$(UV) ruff check --fix .
	$(UV) ruff format .

typecheck:  ## mypy (lenient)
	$(UV) mypy regnav

test: test-unit test-integration  ## Unit + integration tests (no network, no API key)

test-unit:  ## Unit tests
	$(UV) pytest tests/unit -q

test-integration:  ## Integration tests on the synthetic fixture corpus (stub LLM)
	$(UV) pytest tests/integration -q

test-adversarial:  ## Adversarial/safety tests - needs ANTHROPIC_API_KEY
	$(UV) pytest tests/adversarial -m llm -q

coverage:  ## Unit + integration with coverage report (target ~80% on regnav/)
	$(UV) pytest --cov=regnav --cov-report=term-missing --cov-report=xml

regression-gate:  ## Retrieval regression gate on fixtures vs configs/ci_thresholds.yaml
	$(UV) python -m regnav.eval.regression_gate

ingest:  ## Parse, chunk, tag, embed and index data/raw (skips unchanged files)
	$(UV) python -m regnav.cli ingest --config $(CONFIG)

chunks:  ## List chunk ids for gold labelling: make chunks DOC=apra_cps230_2026
	$(UV) python -m regnav.cli chunks --config $(CONFIG) $(if $(DOC),--doc $(DOC),)

ask:  ## Ask one question: make ask Q="..." SECTOR=bank CONFIG=...
	$(UV) python -m regnav.cli ask --config $(CONFIG) --sector $(SECTOR) "$(Q)"

eval:  ## Full eval of one config on the gold set, logged to MLflow
	$(UV) python -m regnav.eval.run_eval --config $(CONFIG)

eval-all:  ## Full eval of all three retrieval configs
	for c in baseline_dense hybrid_pooled hybrid_stratified; do $(UV) python -m regnav.eval.run_eval --config configs/$$c.yaml || exit 1; done

compare:  ## Write docs/results.md comparing the latest run of each config
	$(UV) python -m regnav.eval.compare

judge-calibration:  ## Export judged answers for human labelling / compute Cohen's kappa
	$(UV) python -m regnav.eval.judge calibrate --config $(CONFIG)

release-check:  ## Release gate: tests + regression gate + full eval vs release thresholds
	$(MAKE) lint typecheck test regression-gate
	$(UV) python -m regnav.eval.release_check --config $(CONFIG)

app:  ## Run the Streamlit app locally
	$(UV) streamlit run app/streamlit_app.py

docker-build:  ## Build the app image
	docker build -t au-ai-reg-navigator:latest .

up:  ## docker compose up (app on :8501, MLflow UI on :5000)
	docker compose up --build

down:
	docker compose down

clean:  ## Remove caches (keeps chroma/ and mlruns/)
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov
