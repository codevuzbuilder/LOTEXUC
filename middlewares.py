import logging
import time

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

import cache
import db
from services import get_user, is_admin
from ui import B, Kb, screen

log = logging.getLogger(__name__)
_ok: dict[int, float] = {}


async def missing_channels(bot, uid: int, force: bool = False):
    if cache.setting("sub_enabled", "1") != "1":
        return []
    chans = await db.q("SELECT * FROM channels WHERE active=1")
    if not chans:
        return []
    if not force and time.time() - _ok.get(uid, 0) < 60:
        return []
    missing = []
    for ch in chans:
        try:
            mem = await bot.get_chat_member(ch["chat_id"], uid)
            ok = mem.status in ("creator", "administrator", "member") or (
                mem.status == "restricted" and getattr(mem, "is_member", False))
        except Exception as e:  # bot kanalda admin emas va hokazo — foydalanuvchini to'smaymiz
            log.warning("Obuna tekshirib bo'lmadi (%s): %s", ch["chat_id"], e)
            ok = True
        if not ok:
            missing.append(ch)
    if not missing:
        _ok[uid] = time.time()
    return missing


async def show_sub(ev, missing) -> None:
    kb = Kb()
    for ch in missing:
        if ch["link"]:
            kb.add(B("b_channel", url=ch["link"], title=ch["title"] or "Kanal"))
    kb.add(B("b_check_sub", "chk"))
    await screen(ev, "t_sub", kb)


async def ensure_user(u, ref: int | None):
    if ref and (ref == u.id or not await get_user(ref)):
        ref = None
    await db.x(
        "INSERT OR IGNORE INTO users(id,username,full_name,referrer_id,created_at) VALUES(?,?,?,?,?)",
        u.id, u.username, u.full_name, ref, db.now())
    await db.x("UPDATE users SET username=?, full_name=? WHERE id=?", u.username, u.full_name, u.id)
    return await get_user(u.id)


class Core(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if user is None or user.is_bot:
            return await handler(event, data)
        if isinstance(event, Message) and event.successful_payment:
            return await handler(event, data)  # to'lovni hech qachon to'smaymiz
        ref = None
        if isinstance(event, Message) and event.text and event.text.startswith("/start"):
            parts = event.text.split(maxsplit=1)
            if len(parts) == 2 and parts[1].startswith("ref_") and parts[1][4:].isdigit():
                ref = int(parts[1][4:])
        row = await ensure_user(user, ref)
        data["db_user"] = row
        admin = is_admin(user.id)
        try:
            if row["banned"] and not admin:
                await screen(event, "t_banned")
                return
            if not admin and not (isinstance(event, CallbackQuery) and event.data == "chk"):
                miss = await missing_channels(data["bot"], user.id)
                if miss:
                    await show_sub(event, miss)
                    return
            return await handler(event, data)
        finally:
            if isinstance(event, CallbackQuery):
                try:
                    await event.answer()
                except Exception:
                    pass
