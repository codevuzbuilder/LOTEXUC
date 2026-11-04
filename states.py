from aiogram.fsm.state import State, StatesGroup


class BuyS(StatesGroup):
    pid = State()
    confirm = State()


class TopupS(StatesGroup):
    amount = State()
    check = State()


class AdminS(StatesGroup):
    input = State()
