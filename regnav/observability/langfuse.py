"""Langfuse tracing (cloud; keys from env). No-op when keys are absent.

One trace per query: retrieval span (chunk ids, tiers, scores), one generation per LLM attempt
(prompt, raw output, model, tokens, cost, latency, validation errors), and trace-level metadata
(config name, index version, prompt version, validity). Question text is logged; no user
identifiers or other PII are collected by the app.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from regnav.config import AppConfig, Secrets
from regnav.generate.prompts import SYSTEM_PROMPT, build_user_prompt

log = logging.getLogger(__name__)


def trace_tags(config_name: str, index_version: str, model: str) -> list[str]:
    """Trace tags. The public demo adds ``env:prod`` in front of the config and index."""
    tags = [config_name, index_version, model]
    if os.environ.get("REGNAV_PUBLIC_DEMO") == "1":
        return ["env:prod", *tags]
    return tags


class NoopTracer:
    enabled = False

    def log_answer(self, result: Any, cfg: AppConfig) -> str | None:
        return None

    def flush(self) -> None:
        pass


class LangfuseTracer:
    enabled = True

    def __init__(self, secrets: Secrets) -> None:
        from langfuse import Langfuse

        self.client = Langfuse(
            public_key=secrets.langfuse_public_key,
            secret_key=secrets.langfuse_secret_key,
            host=secrets.langfuse_host,
        )

    def log_answer(self, result: Any, cfg: AppConfig) -> str | None:
        from langfuse import propagate_attributes

        lf = self.client
        meta = {
            "config_name": result.config_name,
            "index_version": result.index_version,
            "prompt_version": result.prompt_version,
            "retrieval_mode": cfg.retrieval.mode,
            "sector": result.sector,
            "valid": result.valid,
            "fallback": result.fallback,
            "abstained": result.answer.abstained,
            "latency_total_s": round(result.total_latency_s, 3),
            "latency_retrieval_s": round(result.retrieval_latency_s, 3),
            "latency_generation_s": round(result.generation_latency_s, 3),
            "cost_usd": result.cost_usd,
            "llm_provider": result.llm_provider,
            "llm_model": result.llm_model,
            "llm_fallback_reason": result.llm_fallback_reason or "",
        }
        with (
            propagate_attributes(
                trace_name="regnav-query",
                tags=trace_tags(result.config_name, result.index_version, cfg.generation.model),
                metadata={k: str(v) for k, v in meta.items()},
                version=result.prompt_version,
            ),
            lf.start_as_current_observation(
                name="regnav-query",
                as_type="chain",
                input={"question": result.question, "sector": result.sector},
            ) as root,
        ):
            with lf.start_as_current_observation(name="retrieve", as_type="retriever") as ret:
                ret.update(
                    input={"query": result.question, "mode": cfg.retrieval.mode},
                    output=[
                        {
                            "chunk_id": c.chunk_id,
                            "rank": c.rank,
                            "tier": c.tier,
                            "modality": c.modality,
                            "score": round(c.score, 5),
                            "scores": {k: round(v, 5) for k, v in c.scores.items()},
                        }
                        for c in result.retrieved
                    ],
                    metadata={
                        "latency_s": round(result.retrieval_latency_s, 3),
                        "index_version": result.index_version,
                    },
                )
            user_prompt = build_user_prompt(result.question, result.retrieved, result.sector)
            for i, a in enumerate(result.attempts, start=1):
                with lf.start_as_current_observation(
                    name=f"generate-attempt-{i}", as_type="generation"
                ) as gen:
                    gen.update(
                        model=a.model,
                        input=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        output=a.raw,
                        usage_details={"input": a.input_tokens, "output": a.output_tokens},
                        cost_details={
                            "input": a.input_tokens * cfg.generation.price_input_per_mtok / 1e6,
                            "output": a.output_tokens * cfg.generation.price_output_per_mtok / 1e6,
                        },
                        metadata={
                            "latency_s": round(a.latency_s, 3),
                            "validation_errors": a.error_types,
                        },
                        level="WARNING" if a.errors else "DEFAULT",
                    )
            root.update(output=result.answer.model_dump(), metadata=meta)
            trace_id = lf.get_current_trace_id()
        return lf.get_trace_url(trace_id=trace_id) if trace_id else None

    def flush(self) -> None:
        self.client.flush()


def get_tracer(secrets: Secrets | None = None) -> NoopTracer | LangfuseTracer:
    secrets = secrets or Secrets()
    if not secrets.langfuse_enabled:
        return NoopTracer()
    try:
        return LangfuseTracer(secrets)
    except Exception as e:
        log.warning("Langfuse disabled: %s", e)
        return NoopTracer()
