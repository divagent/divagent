from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import Base, SessionLocal, engine

# Import models so they register on Base.metadata before create_all.
from nasdaq import Nasdaq, load_nasdaq  # noqa: F401
from nyse import Nyse, load_nyse  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def main():
    return {"message": "Hello World"}


@app.post("/symbols/refresh", tags=["symbols"])
async def refresh_symbols():
    """Fetch the Nasdaq Trader symbol directories and reload both tables.

    - `nasdaq`  <- nasdaqlisted.txt (all rows)
    - `nyse`    <- otherlisted.txt (Exchange == 'N' only)
    """
    async with SessionLocal() as session:
        async with session.begin():
            nasdaq_count = await load_nasdaq(session)
            nyse_count = await load_nyse(session)

    return {
        "status": "ok",
        "nasdaq_rows": nasdaq_count,
        "nyse_rows": nyse_count,
    }
