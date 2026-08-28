from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Edgar
from app.services.upsert import bulk_upsert
from app.utils.edgar import fetch_company_tickers_exchange

# EDGAR exchange labels we keep. NYSE American / Arca / OTC / CBOE are excluded.
KEEP_EXCHANGES = {"Nasdaq", "NYSE"}


async def load_edgar(session: AsyncSession) -> dict[str, int]:
    """Fetch company_tickers_exchange.json, keep NYSE + Nasdaq rows, and upsert
    them into the `edgar` table.

    Returns a per-exchange row count.
    """
    rows = await fetch_company_tickers_exchange()

    values = []
    counts = {"Nasdaq": 0, "NYSE": 0}
    for r in rows:
        ticker = r.get("ticker")
        exchange = r.get("exchange")
        if not ticker or exchange not in KEEP_EXCHANGES:
            continue
        values.append(
            {
                "ticker": ticker,
                "cik": r.get("cik"),
                "name": r.get("name"),
                "exchange": exchange,
            }
        )
        counts[exchange] += 1

    async with session.begin():
        await bulk_upsert(session, Edgar, values)

    return counts
