"""Embedding backends.

* ``sentence_transformers`` - real dense model (default ``BAAI/bge-small-en-v1.5``).
* ``hashing`` - deterministic hashed bag-of-words + bigrams. No download, no network.
  Used by unit/integration tests so they are hermetic; never used for reported results.
"""

from __future__ import annotations

import hashlib
import itertools
import re
from functools import lru_cache
from typing import Protocol

import numpy as np

from regnav.config import EmbeddingConfig

_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "will",
        "with",
        "what",
        "do",
        "does",
        "we",
        "our",
        "us",
        "you",
        "your",
        "how",
        "when",
        "which",
        "who",
    ]
)


class Embedder(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


class HashingEmbedder:
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim
        self.name = f"hashing-{dim}"

    def _features(self, text: str) -> list[str]:
        words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP]
        return words + [f"{a}_{b}" for a, b in itertools.pairwise(words)]

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for f in self._features(text):
            h = int.from_bytes(hashlib.md5(f.encode()).digest()[:8], "little")
            v[h % self.dim] += 1.0 if (h >> 63) == 0 else -1.0
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return (
            np.stack([self._vec(t) for t in texts])
            if texts
            else np.zeros((0, self.dim), np.float32)
        )

    def embed_query(self, text: str) -> np.ndarray:
        return self._vec(text)


class SentenceTransformerEmbedder:
    def __init__(self, cfg: EmbeddingConfig) -> None:
        self.cfg = cfg
        self.name = cfg.model_name
        self._model = None

    @property
    def model(self):  # lazy: importing torch/loading weights is slow
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.cfg.model_name, device=self.cfg.device)
        return self._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self.model.encode(
                texts,
                batch_size=self.cfg.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )

    def embed_query(self, text: str) -> np.ndarray:
        q = f"{self.cfg.query_instruction}{text}"
        return np.asarray(self.model.encode([q], normalize_embeddings=True)[0], dtype=np.float32)


@lru_cache(maxsize=4)
def _cached_st(cfg_json: str) -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder(EmbeddingConfig.model_validate_json(cfg_json))


def get_embedder(cfg: EmbeddingConfig) -> Embedder:
    if cfg.backend == "hashing":
        return HashingEmbedder(cfg.dim)
    return _cached_st(cfg.model_dump_json())
