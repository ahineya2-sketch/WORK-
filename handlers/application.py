import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database.crud import create_application, get_or_create_user, update_application_status
from database.models import ApplicationStatus
from keyboards.common import confirm_application_keyboard, owner_application_keyboard

router = Router()
logger = logging.getLogger(__name__)
settings = get_settings()


class ApplicationFSM(StatesGroup):
    name = State()
    phone = State()
    address = State()
    description = State()
    photo = State()
    confirm = State()


def _summary(data: dict) -> str:
    return (
        "Проверьте заявку:\n"
        f"Имя: {escape(data['name'])}\n"
        f"Телефон: {escape(data['phone'])}\n"
        f"Адрес: {escape(data['address'])}\n"
        f"Описание: {escape(data['description'])}\n"
        f"Фото: {'прикреплено' if data.get('photo') else 'нет'}"
    )


def _owner_text(application_id: int, data: dict) -> str:
    return (
        "🆕 Новая заявка\n"
        f"ID: {application_id}\n"
        f"Имя: {escape(data['name'])}\n"
        f"Телефон: {escape(data['phone'])}\n"
        f"Адрес: {escape(data['address'])}\n"
        f"Описание: {escape(data['description'])}"
    )


async def _save_text_field(message: Message, state: FSMContext, field_name: str) -> str | None:
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return None

    value = message.text.strip()
    if not value:
        await message.answer("Поле не должно быть пустым. Введите значение ещё раз.")
        return None

    await state.update_data(**{field_name: value})
    return value


@router.message(F.text == "Создать заявку")
async def create_application_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ApplicationFSM.name)
    await message.answer("Введите ваше имя:")


@router.message(ApplicationFSM.name)
async def collect_name(message: Message, state: FSMContext) -> None:
    if not await _save_text_field(message, state, "name"):
        return
    await state.set_state(ApplicationFSM.phone)
    await message.answer("Введите телефон:")


@router.message(ApplicationFSM.phone)
async def collect_phone(message: Message, state: FSMContext) -> None:
    if not await _save_text_field(message, state, "phone"):
        return
    await state.set_state(ApplicationFSM.address)
    await message.answer("Введите адрес:")


@router.message(ApplicationFSM.address)
async def collect_address(message: Message, state: FSMContext) -> None:
    if not await _save_text_field(message, state, "address"):
        return
    await state.set_state(ApplicationFSM.description)
    await message.answer("Опишите проблему:")


@router.message(ApplicationFSM.description)
async def collect_description(message: Message, state: FSMContext) -> None:
    if not await _save_text_field(message, state, "description"):
        return
    await state.set_state(ApplicationFSM.photo)
    await message.answer("Отправьте фото или напишите 'Пропустить'.")


@router.message(ApplicationFSM.photo, F.photo)
async def collect_photo(message: Message, state: FSMContext) -> None:
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    data = await state.get_data()
    await state.set_state(ApplicationFSM.confirm)
    await message.answer(_summary(data), reply_markup=confirm_application_keyboard())


@router.message(ApplicationFSM.photo)
async def skip_photo(message: Message, state: FSMContext) -> None:
    if message.text and message.text.lower() == "пропустить":
        await state.update_data(photo=None)
        data = await state.get_data()
        await state.set_state(ApplicationFSM.confirm)
        await message.answer(_summary(data), reply_markup=confirm_application_keyboard())
        return
    await message.answer("Прикрепите фото или отправьте 'Пропустить'.")


@router.callback_query(ApplicationFSM.confirm, F.data == "app:cancel")
async def cancel_application(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Создание заявки отменено.")
    await callback.answer()


@router.callback_query(ApplicationFSM.confirm, F.data == "app:confirm")
async def confirm_application(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    data = await state.get_data()
    try:
        user = await get_or_create_user(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
        )
        application = await create_application(
            session,
            user_id=user.id,
            name=data["name"],
            phone=data["phone"],
            address=data["address"],
            description=data["description"],
            photo=data.get("photo"),
        )

        owner_text = _owner_text(application.id, data)
        if data.get("photo"):
            await bot.send_photo(
                chat_id=settings.admin_id,
                photo=data["photo"],
                caption=owner_text,
                reply_markup=owner_application_keyboard(application.id),
            )
        else:
            await bot.send_message(
                chat_id=settings.admin_id,
                text=owner_text,
                reply_markup=owner_application_keyboard(application.id),
            )

        await callback.message.edit_text("Заявка принята ✅")
        await callback.answer()
    except Exception:
        logger.exception("Failed to save application")
        await callback.message.edit_text("Ошибка при создании заявки. Попробуйте позже.")
        await callback.answer()
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("status:"))
async def change_status(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user.id != settings.admin_id:
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    try:
        _, app_id_str, status_str = callback.data.split(":", maxsplit=2)
        app_id = int(app_id_str)
        status = ApplicationStatus(status_str)
    except (ValueError, TypeError):
        await callback.answer("Некорректные данные")
        return

    application = await update_application_status(session, app_id, status)
    if not application:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    await callback.answer(f"Статус обновлён: {status.value}")
    await callback.message.edit_reply_markup(reply_markup=owner_application_keyboard(application.id))
