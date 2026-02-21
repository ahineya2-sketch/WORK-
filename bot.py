import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.session import SessionLocal
from handlers import admin, application, start


class DbSessionMiddleware:
    async def __call__(self, handler, event: TelegramObject, data: dict):
        async with SessionLocal() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            finally:
                if isinstance(session, AsyncSession):
                    await session.close()


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    setup_logging()
    settings = get_settings()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(start.router)
    dp.include_router(application.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
