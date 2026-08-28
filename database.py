import ssl

from dotenv import load_dotenv
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

# Admin URL is used because this endpoint creates tables (DDL) and bulk-writes.
DATABASE_URL = os.environ["DIV_AIVEN_ADMIN"]

# Aiven requires TLS. asyncpg wants an SSLContext (not a libpq "sslmode" string).
# We negotiate TLS but skip cert verification to avoid shipping the Aiven CA file.
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": _ssl_ctx},
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
