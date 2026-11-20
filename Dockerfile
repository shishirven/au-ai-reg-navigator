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
COPY --chown=app:app data ./data
COPY --chown=app:app pyproject.toml README.md serve.sh ./
# Secrets come from the environment only and are never copied into the image.
# chroma/ is built below as uid 1000. docker-compose mounts hide data/ and chroma/.
ENV REGNAV_CONFIG=configs/prod.yaml \
    REGNAV_PUBLIC_DEMO=1 \
    PORT=8501 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TOKENIZERS_PARALLELISM=false
RUN mkdir -p chroma mlruns results \
    && chown -R app:app chroma mlruns results /app/serve.sh \
    && chmod 755 /app/serve.sh
USER app
# Bake the index. HF_HUB_OFFLINE is already set, so this uses the models copied above.
# The version assert fails the build if the corpus or ingest code drifted from the eval.
# GIT_SHA is applied after this layer so a new commit does not rebuild the index.
RUN python -m regnav.cli ingest --config configs/prod.yaml \
    && python -c "from regnav.config import load_config; from regnav.ingest.index import load_manifest; m=load_manifest(load_config('configs/prod.yaml')); v=m['index_version']; assert v=='idx-2185d086e9c4', v; print('baked', v, 'chunks', m['total_chunks'])"
USER root
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}
RUN printf '%s\n' "$GIT_SHA" > /app/REVISION && chown app:app /app/REVISION
USER app
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import os,urllib.request,sys; p=os.environ.get('PORT','8501'); r=urllib.request.urlopen(f'http://127.0.0.1:{p}/_stcore/health', timeout=4); sys.exit(0 if r.status==200 else 1)"
CMD ["sh", "/app/serve.sh"]
