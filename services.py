import logging
import time

import config
import cache
import db
from ui import T, esc, fmt_money, send_fresh, Kb

log = logging.getLogger(__name__)
_username: str | None = None


def is_admin(uid: int) -> bool:
    return uid in config.ADMIN_IDS or uid in cache.admins_db


def all_admins() -> set[int]:
    return set(config.ADMIN_IDS) | set(cache.admins_db)


async def bot_username(bot) -> str:
    global _username
    if not _username:
        _username = (await bot.me()).username
    return _username


async def get_user(uid: int):
    return await db.q1("SELECT * FROM users WHERE id=?", uid)


def uvars(u) -> dict:
    return {"name": esc(u["full_name"] or "do'st"), "id": u["id"], "balance": fmt_money(u["balance"])}


async def notify_user(bot, uid: int, key: str, kb: Kb | None = None, **vars) -> bool:
    u = await get_user(uid)
    v = {**(uvars(u) if u else {}), **vars}
    text, mt, mid = T(key, **v)
    try:
        await send_fresh(bot, uid, text, kb, mt, mid)
        return True
    except Exception as e:
        log.info("Foydalanuvchiga yuborib bo'lmadi %s: %s", uid, e)
        return False


async def notify_admins(bot, text: str, kb: Kb | None = None, mt=None, mid=None) -> None:
    for aid in all_admins():
        try:
            await send_fresh(bot, aid, text, kb, mt, mid)
        except Exception as e:
            log.info("Adminga yuborib bo'lmadi %s: %s", aid, e)


async def credit(bot, uid: int, amount: int, reward_ref: bool = True) -> int:
    await db.x("UPDATE users SET balance=balance+? WHERE id=?", amount, uid)
    if reward_ref:
        await _ref_reward(bot, uid)
    return (await get_user(uid))["balance"]


async def _ref_reward(bot, uid: int) -> None:
    u = await get_user(uid)
    if not u or not u["referrer_id"] or u["ref_rewarded"]:
        return
    _, rc = await db.x("UPDATE users SET ref_rewarded=1 WHERE id=? AND ref_rewarded=0", uid)
    bonus = cache.int_setting("ref_bonus")
    if rc != 1 or bonus <= 0:
        return
    ref = u["referrer_id"]
    await db.x("UPDATE users SET balance=balance+?, ref_earned=ref_earned+? WHERE id=?", bonus, bonus, ref)
    rb = (await get_user(ref))
    if rb:
        await notify_user(bot, ref, "t_ref_bonus", bonus=fmt_money(bonus))


def ts(t: int | None) -> str:
    return time.strftime("%d.%m.%Y %H:%M", time.gmtime((t or 0) + 5 * 3600))
