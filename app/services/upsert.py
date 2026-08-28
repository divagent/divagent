from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession


async def bulk_upsert(session: AsyncSession, model, values: list[dict]) -> int:
    """Insert rows, updating existing ones on primary-key conflict.

    No deletes: rows missing from the source (e.g. delisted) are left as-is.
    """
    if not values:
        return 0

    table = model.__table__
    pk_cols = {c.name for c in table.primary_key.columns}

    # Dedupe within the batch (last occurrence wins); ON CONFLICT cannot touch
    # the same row twice in one statement.
    deduped: dict[tuple, dict] = {}
    for row in values:
        deduped[tuple(row[c] for c in pk_cols)] = row
    values = list(deduped.values())

    stmt = pg_insert(table).values(values)
    update_cols = {
        c.name: getattr(stmt.excluded, c.name)
        for c in table.columns
        if c.name not in pk_cols
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=list(pk_cols),
        set_=update_cols,
    )
    await session.execute(stmt)
    return len(values)
