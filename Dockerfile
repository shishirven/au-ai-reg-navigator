# syntax=docker/dockerfile:1.7
# AU AI Regulation Navigator - Streamlit app image (CPU-only).
#   docker build -t au-ai-reg-navigator .
# Behind a TLS-inspecting corporate proxy, pass its CA bundle as a BuildKit secret:
#   docker build --secret id=ca_bundle,src=/path/to/ca.pem --build-arg HTTPS_PROXY=... .

ARG PYTHON_VERSION=3.12

# ---------------------------------------------------------------- builder
FROM python:${PYTHON_VERSION}-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    HF_HOME=/app/.cache/huggingface \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# Optional extra CA (corporate proxy) - never stored in the image.
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -f /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi && \
    pip install --no-cache-dir uv==0.11.32

# 1) dependencies only (cached layer); torch comes from the CPU-only index pinned in uv.lock
COPY pyproject.toml uv.lock .python-version README.md ./
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -f /run/secrets/ca_bundle ]; then export SSL_CERT_FILE=/run/secrets/ca_bundle; fi && \
    uv sync --frozen --no-dev --no-install-project

# 2) the project itself
COPY regnav ./regnav
RUN uv sync --frozen --no-dev

# 3) bake the embedding model and the re-ranking model into the image (the runtime is offline)
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -f /run/secrets/ca_bundle ]; then export SSL_CERT_FILE=/run/secrets/ca_bundle REQUESTS_CA_BUNDLE=/run/secrets/ca_bundle; fi && \
    /app/.venv/bin/python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('BAAI/bge-small-en-v1.5'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# ---------------------------------------------------------------- runtime
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PATH=/app/.venv/bin:$PATH \
    HF_HOME=/app/.cache/huggingface \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PYTHONUNBUFFERED=1 \
    ANONYMIZED_TELEMETRY=False \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/.cache /app/.cache
COPY --chown=app:app regnav ./regnav
COPY --chown=app:app app ./app
COPY --chown=app:app configs ./configs
COPY --chown=app:app pyproject.toml README.md ./
# data/, chroma/, mlruns/ and results/ are mounted as volumes (see docker-compose.yml);
# secrets come from env_file only and are never copied into the image.
RUN mkdir -p data chroma mlruns results && chown -R app:app data chroma mlruns results
USER app
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4).status == 200 else 1)"
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
