"""Agent-runner predict endpoint (internal).

`POST /api/v1/predict/research` runs the Strands research agent (layer 3) over the
divmcp tools and returns a structured `ResearchLayer`. divagent is agents-only and
not browser-facing — this is called by divcore, which computes the deterministic
facts/pattern layers, forwards them here, and owns calendar publishing.

Gated by the shared `X-Trace-Secret` header (TRACE_SECRET, forwarded by divcore).
A miss returns 404 so the endpoint's existence isn't confirmed to a prober.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.agent.predict import research
from app.core.config import settings
from app.schemas.predict import ResearchLayer, ResearchRequest

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("/research", response_model=ResearchLayer)
async def predict_research(
    req: ResearchRequest,
    x_trace_secret: str | None = Header(default=None),
) -> ResearchLayer:
    secret = settings.TRACE_SECRET
    if not secret or x_trace_secret != secret:
        raise HTTPException(status_code=404)

    return await research(req, trace_id=f"predict:{req.ticker.strip().upper()}")
