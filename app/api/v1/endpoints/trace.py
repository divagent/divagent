"""Agent-runner trace endpoint (internal).

`POST /api/v1/trace/analyze?q=CNQ.TO` runs the Strands analyze agent and streams a
source-tagged NDJSON trace (you / fastapi / agent / mcp) of every step. divagent is
agents-only and not browser-facing — this is called by divcore, which re-streams it
to the frontend's secret trace page.

Gated by the `X-Internal-Key` header (shared with divcore as INTERNAL_SERVICE_KEY).
A miss returns 404 so the endpoint's existence isn't confirmed to a prober.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agent.trace import stream_analyze
from app.core.config import settings

router = APIRouter(prefix="/trace", tags=["trace"])


@router.post("/analyze")
async def trace_analyze(
    q: str = Query(..., description="Ticker or question, e.g. 'CNQ.TO'"),
    x_internal_key: str | None = Header(default=None),
) -> StreamingResponse:
    key = settings.INTERNAL_SERVICE_KEY
    if not key or x_internal_key != key:
        raise HTTPException(status_code=404)

    async def body():
        async for event in stream_analyze(q):
            yield json.dumps(event, default=str) + "\n"

    return StreamingResponse(body(), media_type="application/x-ndjson")
