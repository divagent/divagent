import httpx

COMPANY_TICKERS_EXCHANGE_URL = (
    "https://www.sec.gov/files/company_tickers_exchange.json"
)

# SEC requires a descriptive User-Agent with contact info, else it returns 403.
_HEADERS = {"User-Agent": "divagent/0.1 (admin@divagent.local)"}


async def fetch_company_tickers_exchange() -> list[dict]:
    """Fetch SEC's company_tickers_exchange.json and return rows as dicts.

    The file has the shape {"fields": [...], "data": [[...], ...]}; this
    zips each data row against the field names.
    """
    async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
        resp = await client.get(COMPANY_TICKERS_EXCHANGE_URL)
        resp.raise_for_status()
        payload = resp.json()

    fields = payload.get("fields", [])
    return [dict(zip(fields, row)) for row in payload.get("data", [])]
