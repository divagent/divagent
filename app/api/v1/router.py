from fastapi import APIRouter

from app.api.v1.endpoints import edgar, market, predict, symbols, trace

api_router = APIRouter()
api_router.include_router(symbols.router)
api_router.include_router(edgar.router)
api_router.include_router(trace.router)
api_router.include_router(predict.router)
api_router.include_router(market.router)
