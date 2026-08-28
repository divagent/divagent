from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from common import fetch_pipe_file, to_bool, to_int
from nyse.model import Nyse

OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


async def load_nyse(session: AsyncSession) -> int:
    """Fetch otherlisted.txt, keep only NYSE rows (Exchange == 'N'), and
    fully reload the `nyse` table.

    Returns the number of rows written.
    """
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
