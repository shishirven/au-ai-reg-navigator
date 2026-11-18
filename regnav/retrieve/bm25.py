"""Keyword retrieval with BM25 (Okapi) over the same chunk texts (incl. their prefix)."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from regnav.retrieve.base import Filters, RetrievedChunk, rerank

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
        "i",
        "me",
        "my",
        "can",
        "should",
        "must",
        "any",
        "there",
        "their",
        "they",
        "them",
    ]
)


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text.lower())
    return [_stem(t) for t in toks if t not in _STOP and len(t) > 1]


def _stem(t: str) -> str:
    """Tiny suffix stripper (plural/ing/ed) - enough to match 'providers' to 'provider'."""
    for suf in ("ings", "ing", "ies", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 4:
            return t[: -len(suf)] + ("y" if suf == "ies" else "")
    return t


class BM25Retriever:
    name = "bm25"

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.bm25 = BM25Okapi([tokenize(r["text"]) for r in rows]) if rows else None

    def search(self, query: str, k: int, filters: Filters) -> list[RetrievedChunk]:
        if self.bm25 is None or k <= 0:
            return []
        scores = np.asarray(self.bm25.get_scores(tokenize(query)))
        order = np.argsort(-scores, kind="stable")
        out: list[RetrievedChunk] = []
        for i in order:
            row = self.rows[int(i)]
            if scores[i] <= 0 or not filters.matches(row):
                continue
            meta = {k_: v for k_, v in row.items() if k_ != "text"}
            out.append(
                RetrievedChunk(
                    row["chunk_id"],
                    row["text"],
                    meta,
                    float(scores[i]),
                    scores={"bm25": float(scores[i])},
                )
            )
            if len(out) >= k:
                break
        return rerank(out)
