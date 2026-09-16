"""Layer-3 research prediction as a Strands agent over the divmcp tools.

This is the migration of divcore's old hand-rolled `research_prediction` onto the
SAME pipeline as `analyze`/`trace`: discover tools over MCP, run the Strands
reason -> call-tool -> observe loop, and this time coerce the final answer to a
structured `ResearchVerdict` (Strands' `structured_output_model`).

What changed vs. the old routine:
  * data-gathering (declared filings, news, forum chatter) is no longer a fixed
    divcore pipeline — the agent DISCOVERS and drives divmcp's `dividend_tracker`
    (declared truth), `web_search`, and `fetch_url` itself;
  * the single templated Gemini JSON call is replaced by the agentic loop plus
    Strands' structured output.

What did NOT change: the product rule that a weak signal is never dropped. On any
failure we still return a LOW-confidence layer that falls back to the pattern's
next projected payment — this function never raises.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from strands import Agent

# Reuse the exact MCP client + model builders the analyze/trace loop uses so all
# three agents share one topology (tools discovered from divmcp, one model).
from app.agent.analyze import _build_mcp_client, _build_model
from app.core.config import settings
from app.schemas.predict import (
    PatternLayer,
    PredictedNext,
    ResearchLayer,
    ResearchRequest,
    ResearchVerdict,
)

# The skeptical-forecaster prompt (moved here from divcore's age_predictor), adapted
# so the agent uses divmcp's tools for the facts instead of being handed a pre-built
# SIGNALS block. The two-layer discipline (declared check, then leading read) is the
# same; the difference is the agent now does the reaching itself.
RESEARCH_SYSTEM_PROMPT = (
    "You are a skeptical dividend-forecasting analyst. You are given a company's "
    "CONFIRMED past dividends, a mechanically-detected PATTERN, and verified FACTS "
    "(price, yield, amount trend). The past facts and pattern are authoritative — do "
    "NOT contradict them. Your job is the forward-looking question the pattern cannot "
    "answer.\n\n"
    "You have tools. USE them — never guess a hard figure:\n"
    "  * `dividend_tracker` — the deterministic source of the DECLARED dividend "
    "(amount, ex-date, pay-date). Always check it first.\n"
    "  * `web_search` + `fetch_url` — discover and READ leading signals a company may "
    "cut, suspend, or raise its dividend BEFORE any official announcement (analyst "
    "'dividend at risk' notes, guidance cuts, payout ratio over ~100%, "
    "negative/declining free cash flow, insider selling, forum cut-chatter). "
    "Corroborate a claim across independent sources; prefer agreement + recency.\n\n"
    "Work in two layers:\n"
    "1) DECLARED CHECK: If the board has already DECLARED the next dividend, use that "
    "exact amount and ex-date as predictedNext (this is fact, not a guess), set "
    "confidence high, and fill `declared` with what you found.\n"
    "2) LEADING READ: If the next payment is NOT yet declared, decide whether the "
    "company will keep paying on this pattern. RED FLAGS lower confidence and can flip "
    "direction to 'down'. Do NOT assume continuation just because the past was regular "
    "— the whole point is to see a cut coming before it is announced.\n\n"
    "Set `direction` relative to the most recent confirmed dividend. Cite ONLY URLs "
    "you actually retrieved with your tools; never invent numbers or sources. Never "
    "refuse — if signal is weak, return a LOW-confidence read, do not drop it."
)


def _facts_text(facts) -> str:
    lines = [f"  {d.exDate}: {d.amount}" for d in facts.confirmed]
    out = "Confirmed past-year dividends (authoritative):\n" + ("\n".join(lines) or "  (none)")
    if facts.specials:
        out += "\nSpecials (excluded from cadence): " + ", ".join(
            f"{d.exDate}={d.amount}" for d in facts.specials
        )
    if facts.notes:
        out += "\nNotes: " + " | ".join(facts.notes)
    return out


def _pattern_text(pattern: PatternLayer) -> str:
    proj = ", ".join(f"{p.exDate}~${p.amount}" for p in pattern.projected) or "(none)"
    return (
        f"frequency={pattern.frequency}, paymentsPerYear={pattern.paymentsPerYear}, "
        f"typicalAmount={pattern.typicalAmount}, trend={pattern.amountTrend}, "
        f"regular={pattern.regular}\nSummary: {pattern.summary}\nProjected next: {proj}"
    )


def _default_next(pattern: PatternLayer) -> PredictedNext:
    """A sensible predictedNext that never contradicts the pattern (fallback floor)."""
    return PredictedNext(
        exDate=pattern.projected[0].exDate if pattern.projected else None,
        amount=pattern.projected[0].amount if pattern.projected else pattern.typicalAmount,
        direction="up" if pattern.amountTrend == "increasing"
        else "down" if pattern.amountTrend == "decreasing"
        else "constant",
    )


def _fallback(pattern: PatternLayer, model_label: str, generated_at: str) -> ResearchLayer:
    return ResearchLayer(
        willMaintainPattern=pattern.regular,
        confidence=0.0,
        predictedNext=_default_next(pattern),
        reasoning=(
            f"Could not complete agent research (model: {model_label}); falling back "
            "to the detected pattern as a LOW-confidence prediction rather than "
            "dropping it."
        ),
        sources=[],
        model=model_label,
        generatedAt=generated_at,
    )


def _build_prompt(req: ResearchRequest) -> str:
    today = req.today or date.today().isoformat()
    name = req.companyName or req.ticker
    risk = f"\nAutomated risk hint: {req.riskHint}" if req.riskHint else ""
    return (
        f"Today is {today}. Company: {name} ({req.ticker}).\n\n"
        f"=== CONFIRMED PAST DIVIDENDS ===\n{_facts_text(req.facts)}\n\n"
        f"=== DETECTED PATTERN ===\n{_pattern_text(req.pattern)}\n\n"
        f"=== VERIFIED FACTS (price, yield, trend) ===\n{req.groundingText}{risk}\n\n"
        "Research the forward-looking question using your tools "
        "(dividend_tracker for the declared figure; web_search + fetch_url for leading "
        "signals), then give your structured verdict."
    )


async def research(req: ResearchRequest, *, trace_id: str = "internal") -> ResearchLayer:
    """Run the research agent over divmcp and return a structured `ResearchLayer`.

    Never raises: on any MCP/agent failure it degrades to a LOW-confidence layer
    built from the given pattern (the locked product rule — a weak signal is never
    dropped)."""
    generated_at = datetime.now(timezone.utc).isoformat()
    model_label = settings.AGENT_GEMINI_MODEL
    default_next = _default_next(req.pattern)

    try:
        mcp_client = _build_mcp_client()
        # The MCP session must stay open for discovery AND the whole agent run —
        # same sync-context + async-invoke shape trace.py uses.
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            agent = Agent(
                model=_build_model(),
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                tools=tools,
            )
            result = await agent.invoke_async(
                _build_prompt(req), structured_output_model=ResearchVerdict
            )
            verdict = result.structured_output
            if verdict is None:
                raise ValueError("agent returned no structured output")

        pn = verdict.predictedNext or PredictedNext()
        predicted_next = PredictedNext(
            exDate=pn.exDate or default_next.exDate,
            amount=pn.amount if pn.amount is not None else default_next.amount,
            direction=pn.direction or default_next.direction,
        )
        confidence = max(0.0, min(1.0, float(verdict.confidence or 0.0)))
        return ResearchLayer(
            willMaintainPattern=bool(verdict.willMaintainPattern),
            confidence=confidence,
            predictedNext=predicted_next,
            reasoning=verdict.reasoning or "",
            sources=verdict.sources or [],
            model=model_label,
            generatedAt=generated_at,
            declared=verdict.declared,
        )
    except Exception:  # never drop the layer — degrade to the pattern.
        return _fallback(req.pattern, model_label, generated_at)
