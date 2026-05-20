from collections.abc import Sequence
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.checks import CheckResult


async def save_check_result(session: AsyncSession, check: CheckResult) -> CheckResult:
    try:
        session.add(check)
        await session.commit()
        await session.refresh(check)
        return check
    except Exception:
        await session.rollback()
        raise


async def fetch_checks_since(
    session: AsyncSession, service_id: int, since: datetime
) -> Sequence[CheckResult]:
    result = await session.exec(
        select(CheckResult)
        .where(CheckResult.service_id == service_id)
        .where(CheckResult.checked_at >= since)
        .order_by(CheckResult.checked_at.asc())
    )
    return result.all()
