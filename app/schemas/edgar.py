from pydantic import BaseModel


class EdgarRefreshResult(BaseModel):
    status: str = "ok"
    nasdaq_rows: int
    nyse_rows: int
    total_rows: int
