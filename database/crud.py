from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Application, ApplicationStatus, User


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        if user.username != username:
            user.username = username
            await session.commit()
            await session.refresh(user)
        return user

    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_application(
    session: AsyncSession,
    *,
    user_id: int,
    name: str,
    phone: str,
    address: str,
    description: str,
    photo: str | None,
) -> Application:
    application = Application(
        user_id=user_id,
        name=name,
        phone=phone,
        address=address,
        description=description,
        photo=photo,
        status=ApplicationStatus.NEW,
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


async def update_application_status(
    session: AsyncSession, application_id: int, status: ApplicationStatus
) -> Application | None:
    result = await session.execute(select(Application).where(Application.id == application_id))
    application = result.scalar_one_or_none()
    if not application:
        return None

    application.status = status
    await session.commit()
    await session.refresh(application)
    return application


async def get_application_by_id(session: AsyncSession, application_id: int) -> Application | None:
    result = await session.execute(
        select(Application).options(selectinload(Application.user)).where(Application.id == application_id)
    )
    return result.scalar_one_or_none()


async def get_applications_by_status(
    session: AsyncSession, status: ApplicationStatus, page: int = 1, page_size: int = 5
) -> tuple[list[Application], int]:
    page = max(1, page)
    offset = (page - 1) * page_size

    base_stmt: Select[tuple[Application]] = select(Application).where(Application.status == status)
    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    items_stmt = (
        select(Application)
        .options(selectinload(Application.user))
        .where(Application.status == status)
        .order_by(Application.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = (await session.execute(items_stmt)).scalars().all()
    total_pages = (total + page_size - 1) // page_size
    return items, total_pages


async def get_last_applications(session: AsyncSession, limit: int = 10) -> list[Application]:
    stmt = (
        select(Application)
        .options(selectinload(Application.user))
        .order_by(Application.created_at.desc())
        .limit(limit)
    )
    return (await session.execute(stmt)).scalars().all()
