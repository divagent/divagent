"""Wire schemas for the predict (research) agent endpoint.

Field names are camelCase on purpose: they match the JSON divcore sends/receives
verbatim (which in turn mirrors `src/data/ai-query.contract.md` in the frontend),
so the layer-3 `ResearchLayer` divagent returns drops straight into divcore's
`PredictResponse` with no aliasing.

Only layer 3 lives here. Layers 1 & 2 (facts + pattern) are deterministic and stay
in divcore; they are passed in as inputs so the agent can reason over them without
re-deriving them. Calendar publishing is not the agent's job either — divcore owns
that as a post-step.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---- Shared building blocks (mirror divcore sch_predict) ------------------


class FactDividend(BaseModel):
    exDate: str  # ISO yyyy-mm-dd (ex-dividend date)
    amount: float


class FactsLayer(BaseModel):
    confirmed: List[FactDividend] = Field(default_factory=list)
    specials: List[FactDividend] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ProjectedDividend(BaseModel):
    exDate: str
    amount: float
    label: Literal["estimate"] = "estimate"
    method: str = "pattern"


class PatternLayer(BaseModel):
    frequency: str = "unknown"
    paymentsPerYear: int = 0
    typicalAmount: Optional[float] = None
    amountTrend: Literal["increasing", "decreasing", "stable", "unknown"] = "unknown"
    medianIntervalDays: Optional[int] = None
    regular: bool = False
    summary: str = ""
    projected: List[ProjectedDividend] = Field(default_factory=list)


class ResearchSource(BaseModel):
    title: str = ""
    url: str
    publisher: Optional[str] = None
    publishedAt: Optional[str] = None


class PredictedNext(BaseModel):
    exDate: Optional[str] = None
    amount: Optional[float] = None
    direction: Literal["up", "down", "constant"] = "constant"


class DeclaredDividend(BaseModel):
    exDate: Optional[str] = None
    amount: Optional[float] = None
    declarationDate: Optional[str] = None
    payDate: Optional[str] = None
    note: Optional[str] = None


# ---- Request -------------------------------------------------------------


class ResearchRequest(BaseModel):
    """Everything the agent needs to reason about layer 3, computed by divcore.

    `facts` and `pattern` are authoritative and must not be contradicted. The
    quantitative grounding (price/yield/trend) is pre-computed by divcore and passed
    as text so divagent stays lean — the agent's own work is the tool-driven
    research, not the arithmetic.
    """

    ticker: str
    companyName: Optional[str] = None
    currency: Optional[str] = None
    today: Optional[str] = None  # ISO yyyy-mm-dd; defaults to the agent's today
    facts: FactsLayer = Field(default_factory=FactsLayer)
    pattern: PatternLayer = Field(default_factory=PatternLayer)
    groundingText: str = ""
    riskHint: Optional[str] = None


# ---- What the model fills (structured output) ----------------------------


class ResearchVerdict(BaseModel):
    """The structured shape the Strands agent emits as its final answer.

    Deliberately narrower than `ResearchLayer`: no `model`/`generatedAt` (server
    stamps those). `confidence` is unconstrained here so a slightly out-of-range
    model value never fails validation — the agent module clamps it to 0..1.
    """

    willMaintainPattern: bool = True
    confidence: float = 0.0
    predictedNext: PredictedNext = Field(default_factory=PredictedNext)
    reasoning: str = ""
    sources: List[ResearchSource] = Field(default_factory=list)
    declared: Optional[DeclaredDividend] = None


# ---- Response (layer 3) --------------------------------------------------


class ResearchLayer(BaseModel):
    willMaintainPattern: bool = True
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    predictedNext: PredictedNext = Field(default_factory=PredictedNext)
    reasoning: str = ""
    sources: List[ResearchSource] = Field(default_factory=list)
    model: Optional[str] = None
    generatedAt: Optional[str] = None
    # Set when the board has already DECLARED the next dividend (fact, not a guess);
    # divcore promotes it to a 'Declared' calendar row via reconcile. None otherwise.
    declared: Optional[DeclaredDividend] = None
