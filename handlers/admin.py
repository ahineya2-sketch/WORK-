from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.crud import get_applications_by_status
from database.models import Application, ApplicationStatus
from keyboards.inline import admin_pagination_keyboard, admin_status_keyboard

router = Router()
settings = get_settings()
PAGE_SIZE = 5


def is_admin(telegram_id: int | None) -> bool:
    return telegram_id == settings.admin_id


def render_application_card(application: Application) -> str:
    return (
        f"#{application.id} | {application.created_at:%Y-%m-%d %H:%M}\n"
        f"Имя: {escape(application.name)}\n"
        f"Телефон: {escape(application.phone)}\n"
        f"Адрес: {escape(application.address)}\n"
        f"Описание: {escape(application.description)}\n"
        f"Фото: {'есть' if application.photo else 'нет'}"
    )


@router.message(Command("admin"))
async def admin_panel(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Доступ запрещён.")
        return

    new_apps, new_total_pages = await get_applications_by_status(
        session=session,
        status=ApplicationStatus.NEW,
        page=1,
        page_size=PAGE_SIZE,
    )

    if not new_apps:
        await message.answer("Админ-панель. Новых заявок пока нет.", reply_markup=admin_status_keyboard())
        return

    text = "Новые заявки, страница 1:\n\n" + "\n\n".join(render_application_card(item) for item in new_apps)
    await message.answer(
        text,
        reply_markup=admin_pagination_keyboard(ApplicationStatus.NEW.value, 1, new_total_pages),
    )
    await message.answer("Фильтр по статусам:", reply_markup=admin_status_keyboard())


@router.callback_query(F.data == "admin:noop")
async def admin_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("admin:list:"))
async def admin_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id if callback.from_user else None):
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    try:
        _, _, status_raw, page_raw = (callback.data or "").split(":", maxsplit=3)
        status = ApplicationStatus(status_raw)
        page = max(1, int(page_raw))
    except (ValueError, TypeError):
        await callback.answer("Некорректные параметры", show_alert=True)
        return

    apps, total_pages = await get_applications_by_status(
        session=session,
        status=status,
        page=page,
        page_size=PAGE_SIZE,
    )

    text = f"Заявки со статусом «{status.value}», страница {page}:"
    if apps:
        text += "\n\n" + "\n\n".join(render_application_card(item) for item in apps)
    else:
        text += "\n\nСписок пуст."

    if callback.message:
        await callback.message.edit_text(
            text,
            reply_markup=admin_pagination_keyboard(status.value, page, total_pages),
        )
    await callback.answer()
