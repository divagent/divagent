from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from common import fetch_pipe_file, to_bool, to_int
from nasdaq.model import Nasdaq

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"


async def load_nasdaq(session: AsyncSession) -> int:
    """Fetch nasdaqlisted.txt and fully reload the `nasdaq` table.

    Returns the number of rows written.
    """
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
