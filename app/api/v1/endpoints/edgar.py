from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.edgar import EdgarRefreshResult
from app.services.edgar_loader import load_edgar

router = APIRouter(prefix="/edgar", tags=["edgar"])


@router.post("/refresh", response_model=EdgarRefreshResult)
async def refresh_edgar(session: AsyncSession = Depends(get_session)):
    """Fetch SEC EDGAR's company_tickers_exchange.json and upsert the
    NYSE + Nasdaq rows (cik, ticker, name, exchange) into the `edgar` table.
    """
    counts = await load_edgar(session)
    return EdgarRefreshResult(
        nasdaq_rows=counts["Nasdaq"],
        nyse_rows=counts["NYSE"],
        total_rows=counts["Nasdaq"] + counts["NYSE"],
    )
