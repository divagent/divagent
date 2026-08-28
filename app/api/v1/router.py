from fastapi import APIRouter

from app.api.v1.endpoints import symbols

api_router = APIRouter()
api_router.include_router(symbols.router)
