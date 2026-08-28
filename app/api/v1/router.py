from fastapi import APIRouter

from app.api.v1.endpoints import edgar, symbols

api_router = APIRouter()
api_router.include_router(symbols.router)
api_router.include_router(edgar.router)
