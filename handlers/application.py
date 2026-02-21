import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.crud import create_application, get_or_create_user, update_application_status
from database.models import ApplicationStatus
from keyboards.inline import application_status_keyboard, confirm_application_keyboard
from states.application import ApplicationState

router = Router()
settings = get_settings()
logger = logging.getLogger(__name__)


def build_summary(data: dict[str, str | None]) -> str:
    return (
        "Проверьте данные заявки:\n\n"
        f"Имя: {escape(data['name'] or '')}\n"
        f"Телефон: {escape(data['phone'] or '')}\n"
        f"Адрес: {escape(data['address'] or '')}\n"
        f"Описание: {escape(data['description'] or '')}\n"
        f"Фото: {'есть' if data.get('photo') else 'нет'}"
    )


def build_admin_text(application_id: int, data: dict[str, str | None]) -> str:
    return (
        "🆕 Новая заявка\n"
        f"ID: {application_id}\n"
        f"Имя: {escape(data['name'] or '')}\n"
        f"Телефон: {escape(data['phone'] or '')}\n"
        f"Адрес: {escape(data['address'] or '')}\n"
        f"Описание: {escape(data['description'] or '')}"
    )


async def save_text_value(message: Message, state: FSMContext, key: str) -> bool:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Введите текстовое значение.")
        return False

    await state.update_data(**{key: text})
    return True


@router.message(F.text == "Создать заявку")
async def create_application_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ApplicationState.name)
    await message.answer("Введите имя:")


@router.message(ApplicationState.name)
async def collect_name(message: Message, state: FSMContext) -> None:
    if not await save_text_value(message, state, "name"):
        return

    await state.set_state(ApplicationState.phone)
    await message.answer("Введите телефон:")


@router.message(ApplicationState.phone)
async def collect_phone(message: Message, state: FSMContext) -> None:
    if not await save_text_value(message, state, "phone"):
        return

    await state.set_state(ApplicationState.address)
    await message.answer("Введите адрес:")


@router.message(ApplicationState.address)
async def collect_address(message: Message, state: FSMContext) -> None:
    if not await save_text_value(message, state, "address"):
        return

    await state.set_state(ApplicationState.description)
    await message.answer("Опишите задачу:")


@router.message(ApplicationState.description)
async def collect_description(message: Message, state: FSMContext) -> None:
    if not await save_text_value(message, state, "description"):
        return

    await state.set_state(ApplicationState.photo)
    await message.answer("Прикрепите фото или напишите «Пропустить».")


@router.message(ApplicationState.photo, F.photo)
async def collect_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo=message.photo[-1].file_id)
    data = await state.get_data()
    await state.set_state(ApplicationState.confirm)
    await message.answer(build_summary(data), reply_markup=confirm_application_keyboard())


@router.message(ApplicationState.photo)
async def skip_photo(message: Message, state: FSMContext) -> None:
    if (message.text or "").strip().lower() != "пропустить":
        await message.answer("Прикрепите фото или отправьте «Пропустить».")
        return

    await state.update_data(photo=None)
    data = await state.get_data()
    await state.set_state(ApplicationState.confirm)
    await message.answer(build_summary(data), reply_markup=confirm_application_keyboard())


@router.callback_query(ApplicationState.confirm, F.data == "app:cancel")
async def cancel_application(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Создание заявки отменено.")
    await callback.answer()


@router.callback_query(ApplicationState.confirm, F.data == "app:confirm")
async def confirm_application(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    data = await state.get_data()

    try:
        user = await get_or_create_user(
            session=session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
        )
        application = await create_application(
            session=session,
            user_id=user.id,
            name=str(data.get("name", "")),
            phone=str(data.get("phone", "")),
            address=str(data.get("address", "")),
            description=str(data.get("description", "")),
            photo=data.get("photo"),
        )

        admin_text = build_admin_text(application.id, data)
        if data.get("photo"):
            await bot.send_photo(
                chat_id=settings.admin_id,
                photo=str(data["photo"]),
                caption=admin_text,
                reply_markup=application_status_keyboard(application.id),
            )
        else:
            await bot.send_message(
                chat_id=settings.admin_id,
                text=admin_text,
                reply_markup=application_status_keyboard(application.id),
            )

        if callback.message:
            await callback.message.edit_text("Заявка принята ✅")
        await callback.answer()
    except Exception:
        logger.exception("Failed to create application")
        if callback.message:
            await callback.message.edit_text("Ошибка при создании заявки. Попробуйте позже.")
        await callback.answer()
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("status:"))
async def change_status(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    try:
        _, application_id_raw, status_raw = (callback.data or "").split(":", maxsplit=2)
        application_id = int(application_id_raw)
        status = ApplicationStatus(status_raw)
    except (ValueError, TypeError):
        await callback.answer("Некорректные данные", show_alert=True)
        return

    application = await update_application_status(session, application_id=application_id, status=status)
    if application is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.answer(f"Статус обновлён: {status.value}")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=application_status_keyboard(application_id))
