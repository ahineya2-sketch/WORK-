import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.crud import get_application_by_id, get_applications_by_status, get_last_applications
from database.models import Application, ApplicationStatus
from keyboards.common import admin_pagination_keyboard, admin_status_keyboard

router = Router()
settings = get_settings()
logger = logging.getLogger(__name__)


def _render_application(app: Application) -> str:
    return (
        f"ID: {app.id}\n"
        f"Статус: {app.status.value}\n"
        f"Имя: {escape(app.name)}\n"
        f"Телефон: {escape(app.phone)}\n"
        f"Адрес: {escape(app.address)}\n"
        f"Описание: {escape(app.description)}\n"
        f"Фото: {'есть' if app.photo else 'нет'}\n"
        f"Создана: {app.created_at:%Y-%m-%d %H:%M}"
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if message.from_user.id != settings.admin_id:
        await message.answer("Доступ запрещён")
        return

    await message.answer(
        "Админ-панель:\n"
        "- /admin_last — последние 10 заявок\n"
        "- /admin_get <id> — заявка по ID\n"
        "Или выберите статус:",
        reply_markup=admin_status_keyboard(),
    )


@router.message(Command("admin_last"))
async def admin_last(message: Message, session: AsyncSession) -> None:
    if message.from_user.id != settings.admin_id:
        await message.answer("Доступ запрещён")
        return

    apps = await get_last_applications(session, limit=10)
    if not apps:
        await message.answer("Заявок пока нет")
        return

    for app in apps:
        await message.answer(_render_application(app))


@router.message(Command("admin_get"))
async def admin_get(message: Message, session: AsyncSession) -> None:
    if message.from_user.id != settings.admin_id:
        await message.answer("Доступ запрещён")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /admin_get <id>")
        return

    app = await get_application_by_id(session, int(parts[1]))
    if not app:
        await message.answer("Заявка не найдена")
        return

    await message.answer(_render_application(app))


@router.callback_query(F.data == "admin:noop")
async def admin_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("admin:list:"))
async def admin_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user.id != settings.admin_id:
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    try:
        _, _, status_str, page_str = callback.data.split(":", maxsplit=3)
        status = ApplicationStatus(status_str)
        page = max(1, int(page_str))
    except (ValueError, TypeError):
        await callback.answer("Некорректные параметры")
        return

    apps, total_pages = await get_applications_by_status(session, status, page=page, page_size=5)
    if not apps:
        await callback.message.edit_text(
            f"По статусу '{status.value}' заявок нет.",
            reply_markup=admin_pagination_keyboard(status.value, page, total_pages),
        )
        await callback.answer()
        return

    text = f"Заявки со статусом '{status.value}', страница {page}:\n\n" + "\n\n".join(
        [f"#{a.id}: {escape(a.name)}, {escape(a.phone)}, {escape(a.address)}" for a in apps]
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_pagination_keyboard(status.value, page, total_pages),
    )
    await callback.answer()
