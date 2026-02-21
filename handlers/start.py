import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_or_create_user
from keyboards.common import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    try:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
        logger.info("User started bot: telegram_id=%s user_id=%s", message.from_user.id, user.id)
        await message.answer(
            "Привет! Я помогу оставить заявку на услуги мастера. Нажмите кнопку ниже.",
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Failed to process /start")
        await message.answer("Произошла ошибка. Попробуйте позже.")
