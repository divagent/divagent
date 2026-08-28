from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Nasdaq, Nyse
from app.utils.nasdaq_files import fetch_pipe_file, to_bool, to_int

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


async def load_nasdaq(session: AsyncSession) -> int:
    """Fetch nasdaqlisted.txt and fully reload the `nasdaq` table."""
    rows = await fetch_pipe_file(NASDAQ_LISTED_URL)

    records = [
        Nasdaq(
            symbol=r["Symbol"],
            security_name=r.get("Security Name"),
            market_category=r.get("Market Category"),
            test_issue=to_bool(r.get("Test Issue")),
            financial_status=r.get("Financial Status"),
            round_lot_size=to_int(r.get("Round Lot Size")),
            etf=to_bool(r.get("ETF")),
            next_shares=to_bool(r.get("NextShares")),
        )
        for r in rows
        if r.get("Symbol")
    ]

    await session.execute(delete(Nasdaq))
    session.add_all(records)
    return len(records)


async def load_nyse(session: AsyncSession) -> int:
    """Fetch otherlisted.txt, keep only NYSE rows (Exchange == 'N'), and
    fully reload the `nyse` table."""
    rows = await fetch_pipe_file(OTHER_LISTED_URL)

    records = [
        Nyse(
            symbol=r["ACT Symbol"],
            security_name=r.get("Security Name"),
            exchange=r.get("Exchange"),
            cqs_symbol=r.get("CQS Symbol"),
            etf=to_bool(r.get("ETF")),
            round_lot_size=to_int(r.get("Round Lot Size")),
            test_issue=to_bool(r.get("Test Issue")),
            nasdaq_symbol=r.get("NASDAQ Symbol"),
        )
        for r in rows
        if r.get("ACT Symbol") and (r.get("Exchange") or "").strip() == "N"
    ]

    await session.execute(delete(Nyse))
    session.add_all(records)
    return len(records)


async def refresh_all(session: AsyncSession) -> tuple[int, int]:
    """Reload both tables inside a single transaction."""
    async with session.begin():
        nasdaq_count = await load_nasdaq(session)
        nyse_count = await load_nyse(session)
    return nasdaq_count, nyse_count
