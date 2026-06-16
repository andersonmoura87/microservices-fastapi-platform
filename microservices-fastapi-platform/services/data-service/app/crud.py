from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Record
from .schemas import RecordCreate


async def create_record(session: AsyncSession, payload: RecordCreate) -> Record:
    record = Record(key=payload.key, payload=payload.payload)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_record(session: AsyncSession, record_id: int) -> Record | None:
    result = await session.execute(select(Record).where(Record.id == record_id))
    return result.scalar_one_or_none()


async def list_records(session: AsyncSession, limit: int = 100) -> list[Record]:
    result = await session.execute(
        select(Record).order_by(Record.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
