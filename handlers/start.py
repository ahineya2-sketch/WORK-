import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_or_create_user
from keyboards.reply import main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    try:
        await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
        await message.answer(
            "Добро пожаловать в сервис «Мастер на час». Нажмите кнопку ниже, чтобы создать заявку.",
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Start handler failed")
        await message.answer("Произошла ошибка. Попробуйте позже.")
