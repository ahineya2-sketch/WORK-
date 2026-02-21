from aiogram.fsm.state import State, StatesGroup


class ApplicationState(StatesGroup):
    name = State()
    phone = State()
    address = State()
    description = State()
    photo = State()
    confirm = State()
