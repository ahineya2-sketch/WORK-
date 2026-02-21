from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Создать заявку")]],
        resize_keyboard=True,
        is_persistent=True,
    )


def confirm_application_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data="app:confirm"),
                InlineKeyboardButton(text="Отменить", callback_data="app:cancel"),
            ]
        ]
    )


def owner_application_keyboard(application_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="В работу", callback_data=f"status:{application_id}:in_progress"),
                InlineKeyboardButton(text="Завершить", callback_data=f"status:{application_id}:done"),
            ]
        ]
    )


def admin_pagination_keyboard(status: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:list:{status}:{page - 1}"))
    buttons.append(InlineKeyboardButton(text=f"{page}/{max(total_pages, 1)}", callback_data="admin:noop"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:list:{status}:{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])


def admin_status_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Новые", callback_data="admin:list:new:1"),
                InlineKeyboardButton(text="В работе", callback_data="admin:list:in_progress:1"),
                InlineKeyboardButton(text="Завершённые", callback_data="admin:list:done:1"),
            ]
        ]
    )
