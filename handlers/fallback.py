from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from handlers.user import go_home
from services import get_user

router = Router(name="fallback")


@router.message(StateFilter(None), F.text)
async def any_text(m: Message, db_user):
    await go_home(m, db_user)


@router.callback_query()
async def stale(cb: CallbackQuery):
    await go_home(cb, await get_user(cb.from_user.id))
