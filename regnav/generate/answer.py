"""Answer a question: retrieve -> prompt -> LLM (structured) -> validate -> (retry once) -> result.

On a second validation failure we return a *safe abstention* rather than an unvalidated answer.
Every result carries the config name and index version (traceability), plus latency/tokens/cost.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from regnav.commencement import Commencement, pending_for
from regnav.config import AppConfig, LLMConfig
from regnav.generate.llm import LLMClient, LLMError, cost_usd, llm_failure_fields
from regnav.generate.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_repair_prompt,
    build_user_prompt,
)
from regnav.generate.schema import DISCLAIMER, StructuredAnswer, answer_json_schema
from regnav.generate.scope import check_scope, corpus_instruments
from regnav.generate.validate import repair_answer, validate_answer
from regnav.retrieve import RetrievalSystem, RetrievedChunk

log = logging.getLogger(__name__)


@dataclass
class Attempt:
    raw: str
    errors: list[str]
    error_types: list[str]
    repairs: list[str]
    input_tokens: int
    output_tokens: int
    latency_s: float
    model: str
    provider: str = ""
    fallback_reason: str | None = None


@dataclass
class AnswerResult:
    query_id: str
    question: str
    sector: str | None
    config_name: str
    index_version: str
    prompt_version: str
    answer: StructuredAnswer
    retrieved: list[RetrievedChunk]
    attempts: list[Attempt] = field(default_factory=list)
    valid: bool = True  # final answer passed validation
    fallback: bool = False  # safe abstention returned after repeated validation failure
    repaired: bool = False  # final answer needed deterministic claim-level repair
    gate_reason: str | None = None  # scope gate abstained before calling the LLM
    error: str | None = None
    retrieval_latency_s: float = 0.0
    generation_latency_s: float = 0.0
    total_latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    trace_url: str | None = None
    # Which model actually produced the final answer (D-041): primary API vs local fallback.
    llm_provider: str = ""
    llm_model: str = ""
    llm_fallback_reason: str | None = None
    disclaimer: str = DISCLAIMER
    # D-056: obligations in this answer that haven't commenced, how the date was stated
    # ({"id", "commences", "source_chunk", "how": "model" | "retry" | "quoted"}).
    commencements: list[dict[str, Any]] = field(default_factory=list)

    @property
    def retrieved_ids(self) -> list[str]:
        return [c.chunk_id for c in self.retrieved]

    def cited(self) -> list[tuple[str, str, str]]:
        """(section, claim, citation_id) for every claim."""
        return [(s, c.claim, c.citation_id) for s, c in self.answer.claims()]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["answer"] = self.answer.model_dump()
        d["retrieved"] = [
            {
                "chunk_id": c.chunk_id,
                "rank": c.rank,
                "score": c.score,
                "tier": c.tier,
                "modality": c.modality,
            }
            for c in self.retrieved
        ]
        return d


def safe_abstention(reason: str) -> StructuredAnswer:
    return StructuredAnswer(abstained=True, abstain_reason=reason)


def answer_question(
    question: str,
    cfg: AppConfig,
    retrieval: RetrievalSystem,
    llm: LLMClient,
    sector: str | None = None,
    tracer: Any | None = None,
    today: date | None = None,
) -> AnswerResult:
    t0 = time.perf_counter()
    chunks = retrieval.search(question, sector=sector)
    t_ret = time.perf_counter() - t0
    result = AnswerResult(
        query_id=uuid.uuid4().hex[:12],
        question=question,
        sector=sector,
        config_name=cfg.name,
        index_version=retrieval.index_version,
        prompt_version=PROMPT_VERSION,
        answer=safe_abstention("No relevant sources were retrieved."),
        retrieved=chunks,
        retrieval_latency_s=t_ret,
    )
    if not chunks:
        result.total_latency_s = time.perf_counter() - t0
        _trace(tracer, result, cfg)
        return result
    gen = cfg.generation
    if gen.scope_gate:
        known = corpus_instruments(str(c.metadata.get("short_name", "")) for c in chunks)
        known |= corpus_instruments(getattr(retrieval, "known_instruments", set()))
        reason = check_scope(question, chunks, known, gen.min_dense_similarity)
        if reason:
            result.gate_reason = reason
            result.answer = safe_abstention(reason)
            result.total_latency_s = time.perf_counter() - t0
            _trace(tracer, result, cfg)
            return result

    pending: list[Commencement] = []
    if gen.commencement_check:
        pending = pending_for(chunks, today or date.today())
        added = _add_commencement_sources(pending, chunks, cfg)
        chunks = chunks + added
        result.retrieved = chunks
    meta = {c.chunk_id: c.metadata for c in chunks}
    messages = [{"role": "user", "content": build_user_prompt(question, chunks, sector, today)}]
    schema = answer_json_schema()
    max_attempts = 1 + cfg.generation.max_validation_retries
    asked_for_date = False
    valid_before_date_retry: StructuredAnswer | None = None
    for attempt in range(max_attempts):
        t_call = time.perf_counter()
        try:
            resp = llm.complete(SYSTEM_PROMPT, messages, schema)
        except LLMError as e:
            if valid_before_date_retry is not None:
                # The date retry couldn't run: keep the valid answer and quote the date.
                missing = [
                    c
                    for c in pending
                    if c.live_source and not _states_date(valid_before_date_retry, c)
                ]
                result.answer = _add_quoted_commencements(valid_before_date_retry, missing, meta)
                result.valid = True
                result.commencements = _commencement_log(pending, missing, asked_for_date=False)
                break
            result.error = str(e)
            result.valid = False
            result.fallback = True
            result.answer = safe_abstention(
                "The language model was unavailable; no answer was generated."
            )
            log.error(
                "llm call failed; abstaining",
                extra={
                    "extra_fields": llm_failure_fields(
                        e,
                        model=cfg.generation.model,
                        elapsed_s=time.perf_counter() - t_call,
                    )
                },
            )
            break
        check = validate_answer(resp.text, meta)
        repairs: list[str] = []
        final = check.answer if check.ok else None
        if (
            check.answer is not None
            and gen.claim_repair
            and (not check.ok or _over_cap(check.answer, gen))
        ):
            repaired, repairs = repair_answer(check.answer, meta, gen.max_claims_per_section)
            recheck = validate_answer(repaired.model_dump_json(), meta)
            final = recheck.answer if recheck.ok else None
        result.attempts.append(
            Attempt(
                resp.text,
                check.errors,
                check.error_types,
                repairs,
                resp.input_tokens,
                resp.output_tokens,
                resp.latency_s,
                resp.model,
                resp.provider,
                resp.fallback_reason,
            )
        )
        result.llm_provider, result.llm_model = resp.provider, resp.model
        result.llm_fallback_reason = resp.fallback_reason
        result.input_tokens += resp.input_tokens
        result.output_tokens += resp.output_tokens
        result.generation_latency_s += resp.latency_s
        if final is not None:
            missing = [c for c in pending if c.live_source and not _states_date(final, c)]
            if missing and attempt < max_attempts - 1:
                # Valid but silent about a start date: one targeted retry, citing the source.
                asked_for_date = True
                valid_before_date_retry = final
                messages = [
                    *messages,
                    {"role": "assistant", "content": resp.text or "{}"},
                    {"role": "user", "content": _commencement_prompt(missing)},
                ]
                continue
            if missing:
                final = _add_quoted_commencements(final, missing, meta)
            result.commencements = _commencement_log(pending, missing, asked_for_date)
            result.answer = final
            result.valid = True
            result.repaired = bool(repairs) and not check.ok
            break
        log.info("validation failed", extra={"extra_fields": {"errors": check.error_types}})
        messages = [
            *messages,
            {"role": "assistant", "content": resp.text or "{}"},
            {"role": "user", "content": build_repair_prompt(check.errors)},
        ]
    else:
        if valid_before_date_retry is not None:
            # The retry for the date failed validation: keep the valid answer, quote the date.
            missing = [
                c for c in pending if c.live_source and not _states_date(valid_before_date_retry, c)
            ]
            result.answer = _add_quoted_commencements(valid_before_date_retry, missing, meta)
            result.valid = True
            result.commencements = _commencement_log(pending, missing, asked_for_date=False)
        else:
            _abstain_after_validation(result, cfg)
    priced: LLMConfig = cfg.generation
    if result.llm_fallback_reason and cfg.generation.fallback is not None:
        priced = cfg.generation.fallback  # the local fallback answered (usually free)
    result.cost_usd = cost_usd(priced, result.input_tokens, result.output_tokens)
    result.total_latency_s = time.perf_counter() - t0
    _trace(tracer, result, cfg)
    return result


def _abstain_after_validation(result: AnswerResult, cfg: AppConfig) -> None:
    result.valid = False
    result.fallback = True
    result.answer = safe_abstention(
        "A reliable, correctly cited answer could not be produced from the retrieved sources."
    )
    log.error(
        "llm abstained after validation",
        extra={
            "extra_fields": {
                "event": "llm_abstained",
                "exception_class": None,
                "http_status": None,
                "error_type": "validation",
                "error_message": "safe abstention after validation",
                "retry_after": None,
                "model": result.llm_model or cfg.generation.model,
                "prompt_tokens": result.input_tokens,
                "completion_tokens": result.output_tokens,
                "elapsed_s": round(result.generation_latency_s, 3),
            }
        },
    )


def _commencement_log(
    pending: list[Commencement], missing: list[Commencement], asked_for_date: bool
) -> list[dict[str, Any]]:
    return [
        {
            "id": c.id,
            "commences": c.commences.isoformat(),
            "source_chunk": c.live_source.chunk if c.live_source else "",
            "how": "quoted" if c in missing else ("retry" if asked_for_date else "model"),
        }
        for c in pending
    ]


_CHUNK_ROWS: dict[str, dict[str, dict[str, Any]]] = {}


def _chunk_row(cfg: AppConfig, chunk_id: str) -> dict[str, Any] | None:
    key = cfg.index_key()
    if key not in _CHUNK_ROWS:
        from regnav.ingest.index import load_chunk_rows

        _CHUNK_ROWS[key] = {r["chunk_id"]: r for r in load_chunk_rows(cfg)}
    return _CHUNK_ROWS[key].get(chunk_id)


def _add_commencement_sources(
    pending: list[Commencement], chunks: list[RetrievedChunk], cfg: AppConfig
) -> list[RetrievedChunk]:
    """The live chunk that states each pending date, if it wasn't retrieved already."""
    have = {c.chunk_id for c in chunks}
    out: list[RetrievedChunk] = []
    for c in pending:
        src = c.live_source
        if src is None or src.chunk in have:
            continue
        row = _chunk_row(cfg, src.chunk)
        if row is None:
            continue
        meta = {k: v for k, v in row.items() if k not in ("text", "chunk_id")}
        out.append(
            RetrievedChunk(
                src.chunk,
                str(row.get("text", "")),
                meta,
                0.0,
                len(chunks) + len(out) + 1,
                {"commencement_source": 1.0},
            )
        )
        have.add(src.chunk)
    return out


def _states_date(answer: StructuredAnswer, c: Commencement) -> bool:
    return any(c.stated_in(claim.claim) for _, claim in answer.claims())


def _commencement_prompt(missing: list[Commencement]) -> str:
    lines = [
        "Your answer is valid, but it relies on guidance about an obligation that has not "
        "commenced yet and does not say when it starts. Return the same answer with one added "
        "claim per item below, stating the commencement date and citing the given source id:"
    ]
    for c in missing:
        src = c.live_source
        assert src is not None
        lines.append(
            f'- {c.short} commences on {c.long_date}. Cite {src.chunk}, which says: "{src.quote}"'
        )
    return "\n".join(lines)


def _add_quoted_commencements(
    answer: StructuredAnswer, missing: list[Commencement], meta: dict[str, dict[str, Any]]
) -> StructuredAnswer:
    """Last resort: a claim quoting the source that states the date, in the section its tier
    requires. Never a date without a citation."""
    from regnav.config import TIER_TO_SECTION
    from regnav.generate.schema import Claim

    data = answer.model_dump()
    for c in missing:
        src = c.live_source
        if src is None or src.chunk not in meta:
            continue
        section = TIER_TO_SECTION.get(str(meta[src.chunk].get("tier")), "regulator_expects")
        data[section] = [*data[section], Claim(claim=src.quote, citation_id=src.chunk).model_dump()]
    return StructuredAnswer.model_validate(data)


def _over_cap(answer: StructuredAnswer, gen) -> bool:
    cap = gen.max_claims_per_section
    return bool(cap) and any(
        len(getattr(answer, s)) > cap for s in ("mandatory", "regulator_expects", "recommended")
    )


def _trace(tracer: Any | None, result: AnswerResult, cfg: AppConfig) -> None:
    if tracer is None:
        return
    try:
        result.trace_url = tracer.log_answer(result, cfg)
    except Exception as e:  # tracing must never break answering
        log.warning("tracing failed: %s", e)
