"""Deterministic query expansion: AI wording -> technology-neutral regulatory vocabulary.

Binding prudential standards never say "AI"; they regulate service providers, information
assets and operational risk. Appending the tech-neutral terms lets dense, BM25 and the reranker
match the binding text. Small, explicit and auditable on purpose (no LLM rewriting). Each rule
mirrors a mapping APRA itself makes (e.g. AI letter: manage AI vendors "as service provider
arrangements under existing prudential standards"). D-042.
"""

from __future__ import annotations

import re

# (trigger pattern, terms appended when it matches)
GLOSSARY: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(AI|model|LLM|GenAI)\s+(vendor|provider|supplier|developer)s?\b|\bthird[- ]party AI\b"
            r"|\b(vendor|supplier|provider)s?\b",
            re.I,
        ),
        "service provider material arrangement material service provider due diligence agreement",
    ),
    (
        re.compile(r"\bAI\s+(system|model|tool|application|solution|platform)s?\b|\bAI\b", re.I),
        "information asset technology operational risk",
    ),
    (
        re.compile(r"\b(outage|incident|failure|breakdown|disruption)s?\b", re.I),
        "operational risk incident disruption critical operation notify APRA",
    ),
    (
        re.compile(r"\b(inventory|register|catalogue)\b", re.I),
        "register classify information assets",
    ),
    (
        re.compile(r"\b(contract|contractual|agreement)s?\b", re.I),
        "formal agreement provisions",
    ),
]


def expand_query(question: str) -> str:
    """Return the question plus tech-neutral terms for every rule that fires (deduplicated)."""
    added: list[str] = []
    for pattern, terms in GLOSSARY:
        if pattern.search(question):
            for t in terms.split():
                if t.lower() not in question.lower() and t not in added:
                    added.append(t)
    return f"{question} {' '.join(added)}" if added else question
