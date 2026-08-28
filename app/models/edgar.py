from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Edgar(Base):
    """SEC EDGAR ticker↔exchange mapping (source: company_tickers_exchange.json).

    Holds only NYSE + Nasdaq rows. All source fields are kept.
    """

    __tablename__ = "edgar"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    cik: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str | None] = mapped_column(String)
    exchange: Mapped[str | None] = mapped_column(String)
