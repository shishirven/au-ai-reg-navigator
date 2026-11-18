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
    top_k: int = 8  # final number of chunks passed to the generator
    candidate_k: int = 40  # per-retriever candidate pool before fusion
    per_tier_k: int = 3  # stratified: quota per tier
    rrf_k: int = 60  # reciprocal-rank-fusion constant (Cormack et al. 2009)
    sector_filter: bool = True


class GenerationConfig(BaseModel):
    provider: Literal["anthropic", "stub"] = "anthropic"
    model: str = "claude-opus-5-5"
    max_tokens: int = 4000
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = "medium"
    # Current Claude models reject sampling params; kept for older models only.
    temperature: float | None = None
    max_validation_retries: int = 1
    # USD per million tokens - used for cost tracking.
    price_input_per_mtok: float = 4.0
    price_output_per_mtok: float = 20.0


class JudgeConfig(BaseModel):
    model: str = "claude-sonnet-5-5"
    max_tokens: int = 2000
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = "medium"
    price_input_per_mtok: float = 2.0
    price_output_per_mtok: float = 10.0


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


DEFAULT_CONFIG = Path("configs/hybrid_stratified.yaml")


def load_config(path: str | Path | None = None, **overrides: object) -> AppConfig:
    """Load a YAML experiment config. ``REGNAV_CONFIG`` env var is the fallback path."""
    path = Path(path or os.environ.get("REGNAV_CONFIG") or DEFAULT_CONFIG)
    data = yaml.safe_load(path.read_text()) or {}
    data.update(overrides)
    return AppConfig.model_validate(data)
