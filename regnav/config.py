"""Typed configuration.

Experiment settings live in YAML files under ``configs/`` (one per experiment) and are
validated into :class:`AppConfig`. Secrets come only from the environment / ``.env`` via
:class:`Secrets` and are never written to YAML, logs or MLflow.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Tier = Literal["binding", "expectation", "voluntary"]
TIERS: tuple[Tier, ...] = ("binding", "expectation", "voluntary")
Sector = Literal["bank", "insurer", "super", "any_business"]
SECTORS: tuple[Sector, ...] = ("bank", "insurer", "super", "any_business")
Modality = Literal["must", "should", "info"]

# Human-readable labels used in prompts, answers and the UI.
TIER_LABELS: dict[str, str] = {
    "binding": "Mandatory (binding standard)",
    "expectation": "Regulator expects",
    "voluntary": "Recommended (voluntary guidance)",
}
# Answer section that each tier is allowed to populate.
TIER_TO_SECTION: dict[str, str] = {
    "binding": "mandatory",
    "expectation": "regulator_expects",
    "voluntary": "recommended",
}
SECTION_TO_TIER: dict[str, str] = {v: k for k, v in TIER_TO_SECTION.items()}


class EmbeddingConfig(BaseModel):
    backend: Literal["sentence_transformers", "hashing"] = "sentence_transformers"
    model_name: str = "BAAI/bge-small-en-v1.5"
    # BGE v1.5 recommends this prefix for short queries against passages.
    query_instruction: str = "Represent this sentence for searching relevant passages: "
    batch_size: int = 32
    dim: int = 384  # only used by the hashing backend
    device: str = "cpu"


class ChunkingConfig(BaseModel):
    strategy: Literal["structural", "fixed"] = "structural"
    max_tokens: int = 350  # structural: split longer paragraphs at (a)/(b)/(c)
    min_tokens: int = 25  # structural: merge smaller chunks into their neighbour
    fixed_size: int = 512
    fixed_overlap: int = 64


class RetrievalConfig(BaseModel):
    mode: Literal["dense", "hybrid", "stratified"] = "stratified"
    top_k: int = 9  # final number of chunks passed to the generator (pooled modes)
    candidate_k: int = 40  # per-retriever candidate pool before fusion
    per_tier_k: int = 3  # stratified: quota per tier (3 tiers x 3 = 9 = top_k)
    rrf_k: int = 60  # reciprocal-rank-fusion constant (Cormack et al. 2009)
    sector_filter: bool = True
    include_superseded: bool = False
    # Opt-in improvements (D-042); defaults keep the original three configs unchanged.
    query_expansion: bool = False  # AI wording -> tech-neutral terms (regnav/retrieve/expand.py)
    rerank: bool = False  # cross-encoder re-ranking of each tier's candidate pool
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    rerank_pool_k: int = 20  # candidates per tier passed to the cross-encoder
    # Opt-in (D-052): fixes for one document taking every slot in a tier (F-12) and for broad
    # questions. Off by default so earlier configs and their results are unchanged.
    per_doc_cap: int | None = None  # max chunks from one document per tier (stratified only)
    per_doc_cap_tiers: list[str] | None = None  # tiers the cap applies to (None = all)
    strip_instructions: bool = False  # drop answer-format instructions before searching
    stage_queries: bool = False  # broad questions: also search playbook stage sub-queries
    max_stages: int = 6
    tier_depth: int = 40  # candidates per tier per query considered by the cap / multi-query merge


Provider = Literal["ollama", "groq", "openai_compat", "anthropic", "stub"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]


class LLMConfig(BaseModel):
    """One LLM endpoint. ``provider`` selects the client; everything else is data."""

    provider: Provider = "ollama"
    model: str = "qwen3:4b"
    max_tokens: int = 1500
    timeout_s: float = 600.0
    # Sampling. Honoured by Ollama; current Claude models reject sampling params, so the
    # Anthropic client never sends them (DECISIONS D-004).
    temperature: float | None = 0.0
    # Ollama-only
    base_url: str = "http://localhost:11434"
    num_ctx: int = 8192  # Ollama's small default silently truncates long prompts
    think: bool = False  # Qwen3 thinking mode off: faster, whole budget goes to the answer
    # How to request JSON (Ollama / OpenAI-compatible): "none" = schema in the prompt only, parsed
    # and checked by our validator (default - grammar-constrained decoding made Qwen3-4B
    # over-abstain, D-023); "json" = generic JSON mode; "schema" = constrained decoding.
    json_mode: Literal["none", "json", "schema"] = "none"
    # Groq / OpenAI-compatible: reasoning control passed through as-is (e.g. Qwen "none",
    # gpt-oss "low"); None = provider default. API key is injected by the network proxy or
    # read from `api_key_env`.
    reasoning_effort: str | None = None
    api_key_env: str = "GROQ_API_KEY"
    max_rate_limit_retries: int = 8
    # Anthropic-only
    effort: Effort | None = "medium"
    # USD per million tokens (0 for local models) - used for cost tracking.
    price_input_per_mtok: float = 0.0
    price_output_per_mtok: float = 0.0
    # Optional local fallback used by the app/CLI when this model is rate-limited or down
    # (never by evaluation runs). D-041.
    fallback: LLMConfig | None = None


class GenerationConfig(LLMConfig):
    max_validation_retries: int = 1
    max_claims_per_section: int = 3
    # Deterministic per-claim repair before asking the LLM again (D-029).
    claim_repair: bool = True
    # Scope gate before generation (D-030): abstain without calling the LLM when the best
    # dense match is very weak or the question names a jurisdiction / instrument not in corpus.
    scope_gate: bool = True
    min_dense_similarity: float = 0.62


class JudgeConfig(LLMConfig):
    model: str = "gemma3:4b"
    max_tokens: int = 800


class PathsConfig(BaseModel):
    raw_dir: Path = Path("data/raw")
    sources_file: Path = Path("data/sources.yaml")
    chroma_dir: Path = Path("chroma")
    manifest_file: Path = Path("chroma/index_manifest.json")
    chunks_file: Path = Path("chroma/chunks.jsonl")
    eval_questions: Path = Path("data/eval/questions.jsonl")
    mlruns_dir: Path = Path("mlruns")
    results_dir: Path = Path("results")


class AppConfig(BaseModel):
    name: str = "default"
    description: str = ""
    seed: int = 42
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    judge: JudgeConfig = Field(default_factory=JudgeConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)

    def index_key(self) -> str:
        """Identity of the index this config needs (embedding + chunking only).

        Configs that differ only in retrieval/generation share one index.
        """
        payload = json.dumps(
            {"embedding": self.embedding.model_dump(), "chunking": self.chunking.model_dump()},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:10]

    def flat_params(self) -> dict[str, str]:
        """Flattened, secret-free params for MLflow / Langfuse metadata."""
        out: dict[str, str] = {}
        for section in ("embedding", "chunking", "retrieval", "generation", "judge"):
            for k, v in getattr(self, section).model_dump().items():
                if k == "api_key_env":  # name of an env var, but keep anything key-like out of logs
                    continue
                out[f"{section}.{k}"] = str(v)
        out["name"] = self.name
        out["seed"] = str(self.seed)
        return out


class Secrets(BaseSettings):
    """Secrets from env / .env. Never log these."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


DEFAULT_CONFIG = Path("configs/hybrid_stratified_rerank.yaml")  # D-055


def load_config(path: str | Path | None = None, **overrides: object) -> AppConfig:
    """Load a YAML experiment config. ``REGNAV_CONFIG`` env var is the fallback path."""
    path = Path(path or os.environ.get("REGNAV_CONFIG") or DEFAULT_CONFIG)
    data = yaml.safe_load(path.read_text()) or {}
    data.update(overrides)
    return AppConfig.model_validate(data)
