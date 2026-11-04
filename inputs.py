"""Admin uchun umumiy "matn kiriting" mexanizmi."""
from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from services import is_admin
from states import AdminS
from ui import A, Kb, show

HANDLERS: dict = {}


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        u = getattr(event, "from_user", None)
        return bool(u and is_admin(u.id))


def on_input(kind: str):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn
    return deco


async def ask(ev, state: FSMContext, kind: str, prompt: str, back: str, **ctx):
    await state.set_state(AdminS.input)
    await state.set_data({"kind": kind, "back": back, "ctx": ctx})
    await show(ev, prompt, Kb().add(A("❌ Bekor qilish", back, "red")))


router = Router(name="inputs")
router.message.filter(IsAdmin())


@router.message(AdminS.input)
async def dispatch(m: Message, state: FSMContext):
    data = await state.get_data()
    h = HANDLERS.get(data.get("kind"))
    if not h:
        await state.clear()
        return
    await h(m, state, data.get("ctx", {}))
