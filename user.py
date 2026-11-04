import math
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

import cache
import db
from middlewares import missing_channels
from services import (all_admins, bot_username, credit, get_user, is_admin, notify_admins,
                      notify_user, uvars)
from states import BuyS, TopupS
from ui import (A, B, Kb, esc, fmt_money, parse_int, premiumize, screen, send_fresh, show)

router = Router(name="user")

STATUS = {"pending": "⏳ Kutilmoqda", "done": "✅ Bajarildi", "canceled": "❌ Bekor qilindi",
          "approved": "✅ Tasdiqlandi", "rejected": "❌ Rad etildi"}


def main_kb(uid: int) -> Kb:
    pairs = [("m_buy", "u:buy"), ("m_topup", "u:topup"), ("m_profile", "u:profile"),
             ("m_orders", "u:orders"), ("m_prices", "u:prices"), ("m_referral", "u:ref"),
             ("m_guides", "u:guides"), ("m_help", "u:help"), ("m_payments", "u:pays"),
             ("m_top", "u:top")]
    kb = Kb()
    for i in range(0, len(pairs), 2):
        kb.add(B(*pairs[i]), B(*pairs[i + 1]))
    if is_admin(uid):
        kb.add(A("⚙️ Admin panel", "a:home", "red"))
    return kb


def home_kb() -> Kb:
    return Kb().add(B("b_home", "home"))


async def go_home(ev, u, first=False):
    await screen(ev, "t_start" if first else "t_menu", main_kb(u["id"]), **uvars(u))


# ---------------- umumiy ----------------
@router.message(CommandStart())
async def start(m: Message, state: FSMContext, db_user):
    await state.clear()
    await go_home(m, db_user, first=True)


@router.message(Command("cancel"))
async def cancel(m: Message, state: FSMContext, db_user):
    await state.clear()
    await go_home(m, db_user)


@router.callback_query(F.data == "home")
async def home(cb: CallbackQuery, state: FSMContext, db_user):
    await state.clear()
    await go_home(cb, await get_user(cb.from_user.id))


@router.callback_query(F.data == "chk")
async def chk(cb: CallbackQuery, bot, db_user):
    if await missing_channels(bot, cb.from_user.id, force=True):
        await cb.answer("❌ Hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
        return
    await go_home(cb, db_user, first=True)


# ---------------- ma'lumot ekranlari ----------------
@router.callback_query(F.data == "u:profile")
async def profile(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    u = await get_user(cb.from_user.id)
    orders = (await db.q1("SELECT COUNT(*) c FROM orders WHERE user_id=?", u["id"]))["c"]
    refs = (await db.q1("SELECT COUNT(*) c FROM users WHERE referrer_id=?", u["id"]))["c"]
    kb = Kb().add(B("m_topup", "u:topup"), B("m_buy", "u:buy")).add(B("b_home", "home"))
    await screen(cb, "t_profile", kb, **uvars(u), orders=orders, refs=refs)


@router.callback_query(F.data == "u:orders")
async def orders(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    rows = await db.q("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", cb.from_user.id)
    if not rows:
        return await screen(cb, "t_orders_empty", home_kb())
    lst = "\n".join(
        f"<b>№{r['id']}</b> • {r['uc']} UC • {fmt_money(r['price'])} • {STATUS[r['status']]}" for r in rows)
    await screen(cb, "t_orders", home_kb(), list=lst)


@router.callback_query(F.data == "u:pays")
async def pays(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    rows = await db.q("SELECT * FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 10", cb.from_user.id)
    if not rows:
        return await screen(cb, "t_payments_empty", home_kb())
    lst = "\n".join(
        f"<b>№{r['id']}</b> • {'⭐ Stars' if r['method'] == 'stars' else '💳 Karta'} • "
        f"{fmt_money(r['amount'])} • {STATUS[r['status']]}" for r in rows)
    await screen(cb, "t_payments", home_kb(), list=lst)


@router.callback_query(F.data == "u:prices")
async def prices(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    rows = await db.q("SELECT * FROM packages WHERE active=1 ORDER BY uc")
    if not rows:
        return await screen(cb, "t_buy_empty", home_kb())
    lst = "\n".join(f"💎 <b>{r['uc']} UC</b> — {fmt_money(r['price'])}" for r in rows)
    await screen(cb, "t_prices", Kb().add(B("m_buy", "u:buy")).add(B("b_home", "home")), list=lst)


@router.callback_query(F.data == "u:ref")
async def referral(cb: CallbackQuery, state: FSMContext, bot):
    await state.clear()
    u = await get_user(cb.from_user.id)
    refs = (await db.q1("SELECT COUNT(*) c FROM users WHERE referrer_id=?", u["id"]))["c"]
    bonus = cache.int_setting("ref_bonus")
    link = f"https://t.me/{await bot_username(bot)}?start=ref_{u['id']}"
    await screen(cb, "t_referral", home_kb(), bonus=fmt_money(bonus) if bonus else "—", refs=refs,
                 earned=fmt_money(u["ref_earned"]), link=link)


@router.callback_query(F.data == "u:top")
async def top(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    rows = await db.q(
        "SELECT u.id, u.full_name, COUNT(r.id) c FROM users u JOIN users r ON r.referrer_id=u.id "
        "GROUP BY u.id ORDER BY c DESC LIMIT 10")
    if not rows:
        return await screen(cb, "t_top_empty", home_kb())
    medals = ["🥇", "🥈", "🥉"]
    lst = "\n".join(
        f"{medals[i] if i < 3 else str(i + 1) + '.'} {esc(r['full_name'])} — <b>{r['c']}</b> ta"
        for i, r in enumerate(rows))
    await screen(cb, "t_top", home_kb(), list=lst)


# ---------------- qo'llanma / yordam ----------------
@router.callback_query(F.data.in_({"u:guides", "u:help"}))
async def docs_list(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    kind = "guide" if cb.data == "u:guides" else "help"
    docs = await db.q("SELECT id,title FROM docs WHERE kind=? ORDER BY id", kind)
    kb = Kb()
    for d in docs:
        kb.add(B("b_doc", f"dc:{d['id']}", title=d["title"]))
    sup = cache.setting("support")
    if kind == "help" and sup:
        kb.add(B("b_support", url=f"https://t.me/{sup}"))
    kb.add(B("b_home", "home"))
    if kind == "guide":
        return await screen(cb, "t_guides" if docs else "t_guides_empty", kb)
    await screen(cb, "t_help", kb)


@router.callback_query(F.data.startswith("dc:"))
async def doc_view(cb: CallbackQuery):
    d = await db.q1("SELECT * FROM docs WHERE id=?", int(cb.data[3:]))
    if not d:
        return await cb.answer("Topilmadi", show_alert=True)
    back = "u:guides" if d["kind"] == "guide" else "u:help"
    kb = Kb().add(B("b_back", back), B("b_home", "home"))
    await show(cb, premiumize(d["text"] or ""), kb, d["media_type"], d["media_id"])


# ---------------- UC sotib olish ----------------
async def show_buy(ev):
    u = await get_user(ev.from_user.id)
    if cache.setting("shop_enabled", "1") != "1":
        return await screen(ev, "t_shop_off", home_kb())
    pk = await db.q("SELECT * FROM packages WHERE active=1 ORDER BY uc")
    if not pk:
        return await screen(ev, "t_buy_empty", home_kb())
    kb = Kb()
    for p in pk:
        kb.add(B("b_pkg", f"pk:{p['id']}", uc=p["uc"], price=fmt_money(p["price"])))
    kb.add(B("b_home", "home"))
    await screen(ev, "t_buy", kb, **uvars(u))


@router.callback_query(F.data == "u:buy")
async def buy_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_buy(cb)


@router.callback_query(F.data.startswith("pk:"))
async def pick(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    if cache.setting("shop_enabled", "1") != "1":
        return await screen(cb, "t_shop_off", home_kb())
    p = await db.q1("SELECT * FROM packages WHERE id=? AND active=1", int(cb.data[3:]))
    if not p:
        return await show_buy(cb)
    await state.set_state(BuyS.pid)
    await state.update_data(pkg=p["id"])
    await screen(cb, "t_ask_pid", Kb().add(B("b_cancel", "u:buy")), uc=p["uc"], price=fmt_money(p["price"]))


@router.message(BuyS.pid, F.text)
async def got_pid(m: Message, state: FSMContext):
    pid = m.text.strip().replace(" ", "")
    if not (pid.isdigit() and 5 <= len(pid) <= 15):
        return await screen(m, "t_bad_pid", Kb().add(B("b_cancel", "u:buy")))
    p = await db.q1("SELECT * FROM packages WHERE id=? AND active=1", (await state.get_data())["pkg"])
    if not p:
        await state.clear()
        return await show_buy(m)
    u = await get_user(m.from_user.id)
    v = dict(uc=p["uc"], price=fmt_money(p["price"]), player_id=esc(pid), **uvars(u))
    if u["balance"] < p["price"]:
        await state.clear()
        kb = Kb().add(B("m_topup", "u:topup")).add(B("b_home", "home"))
        return await screen(m, "t_no_balance", kb, lack=fmt_money(p["price"] - u["balance"]), **v)
    await state.update_data(pid=pid, price=p["price"])
    await state.set_state(BuyS.confirm)
    await screen(m, "t_confirm", Kb().add(B("b_confirm", "buy:ok"), B("b_cancel", "u:buy")), **v)


@router.callback_query(BuyS.confirm, F.data == "buy:ok")
async def confirm(cb: CallbackQuery, state: FSMContext, bot):
    d = await state.get_data()
    await state.clear()
    uid = cb.from_user.id
    p = await db.q1("SELECT * FROM packages WHERE id=? AND active=1", d["pkg"])
    if not p or cache.setting("shop_enabled", "1") != "1":
        return await show_buy(cb)
    if p["price"] != d["price"]:
        await cb.answer("⚠️ Narx o'zgargan. Qaytadan tanlang.", show_alert=True)
        return await show_buy(cb)
    _, rc = await db.x("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?",
                       p["price"], uid, p["price"])
    if rc != 1:
        u = await get_user(uid)
        kb = Kb().add(B("m_topup", "u:topup")).add(B("b_home", "home"))
        return await screen(cb, "t_no_balance", kb, uc=p["uc"], price=fmt_money(p["price"]),
                            lack=fmt_money(p["price"] - u["balance"]), **uvars(u))
    oid, _ = await db.x(
        "INSERT INTO orders(user_id,uc,price,player_id,created_at) VALUES(?,?,?,?,?)",
        uid, p["uc"], p["price"], d["pid"], db.now())
    u = await get_user(uid)
    uname = f"@{u['username']}" if u["username"] else "—"
    akb = Kb().add(A("✅ Bajarildi", f"ao:done:{oid}", "green"), A("❌ Bekor qilish", f"ao:cancel:{oid}", "red"))
    await notify_admins(
        bot, f"🛒 <b>Yangi buyurtma №{oid}</b>\n\n👤 {esc(u['full_name'])} ({uname})\n🆔 <code>{uid}</code>\n"
             f"💎 <b>{p['uc']} UC</b> — {fmt_money(p['price'])}\n🎮 PUBG ID: <code>{esc(d['pid'])}</code>", akb)
    await screen(cb, "t_order_ok", home_kb(), order_id=oid, uc=p["uc"], price=fmt_money(p["price"]),
                 player_id=esc(d["pid"]), **uvars(u))


# ---------------- hisobni to'ldirish ----------------
def _methods():
    stars = cache.setting("stars_enabled", "1") == "1" and cache.int_setting("stars_rate") > 0
    manual = cache.setting("manual_enabled", "1") == "1" and bool(cache.setting("card_number"))
    return stars, manual


@router.callback_query(F.data == "u:topup")
async def topup_menu(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    stars, manual = _methods()
    kb = Kb()
    if stars:
        kb.add(B("b_stars", "tp:stars"))
    if manual:
        kb.add(B("b_manual", "tp:manual"))
    kb.add(B("b_home", "home"))
    u = await get_user(cb.from_user.id)
    await screen(cb, "t_topup" if (stars or manual) else "t_topup_none", kb, **uvars(u))


@router.callback_query(F.data.in_({"tp:stars", "tp:manual"}))
async def topup_method(cb: CallbackQuery, state: FSMContext):
    method = cb.data[3:]
    stars, manual = _methods()
    if (method == "stars" and not stars) or (method == "manual" and not manual):
        return await topup_menu(cb, state)
    await state.set_state(TopupS.amount)
    await state.update_data(method=method)
    await screen(cb, "t_ask_amount", Kb().add(B("b_cancel", "u:topup")),
                 currency=cache.setting("currency"), min=fmt_money(max(1, cache.int_setting("min_topup"))))


@router.message(TopupS.amount, F.text)
async def got_amount(m: Message, state: FSMContext, bot):
    mn = max(1, cache.int_setting("min_topup"))
    amount = parse_int(m.text)
    if amount is None or amount < mn or amount > 1_000_000_000:
        return await screen(m, "t_bad_amount", Kb().add(B("b_cancel", "u:topup")), min=fmt_money(mn))
    method = (await state.get_data())["method"]
    if method == "stars":
        rate = cache.int_setting("stars_rate")
        stars = math.ceil(amount / rate)
        try:
            await bot.send_invoice(
                chat_id=m.chat.id, title="Hisobni to'ldirish",
                description=f"Balansga {fmt_money(amount)} qo'shiladi", payload=f"st:{m.from_user.id}:{amount}",
                currency="XTR", prices=[LabeledPrice(label="Balans", amount=stars)])
        except TelegramBadRequest:
            return await screen(m, "t_bad_amount", Kb().add(B("b_cancel", "u:topup")), min=fmt_money(mn))
        await state.clear()
        return
    await state.update_data(amount=amount)
    await state.set_state(TopupS.check)
    await screen(m, "t_manual", Kb().add(B("b_cancel", "u:topup")), amount=fmt_money(amount),
                 card=esc(cache.setting("card_number")), owner=esc(cache.setting("card_owner", "—")))


@router.message(TopupS.check, F.photo | F.document)
async def got_check(m: Message, state: FSMContext, bot):
    amount = (await state.get_data())["amount"]
    ft, fid = ("photo", m.photo[-1].file_id) if m.photo else ("document", m.document.file_id)
    pid, _ = await db.x(
        "INSERT INTO payments(user_id,method,amount,status,file_id,file_type,created_at) "
        "VALUES(?,?,?,?,?,?,?)", m.from_user.id, "manual", amount, "pending", fid, ft, db.now())
    await state.clear()
    u = await get_user(m.from_user.id)
    uname = f"@{u['username']}" if u["username"] else "—"
    kb = Kb().add(A("✅ Tasdiqlash", f"ap:ok:{pid}", "green"), A("❌ Rad etish", f"ap:no:{pid}", "red"))
    await notify_admins(
        bot, f"💳 <b>Yangi to'lov so'rovi №{pid}</b>\n\n👤 {esc(u['full_name'])} ({uname})\n"
             f"🆔 <code>{u['id']}</code>\n💵 Summa: <b>{fmt_money(amount)}</b>", kb, ft, fid)
    await screen(m, "t_manual_sent", home_kb(), pay_id=pid, amount=fmt_money(amount))


@router.message(TopupS.check)
async def bad_check(m: Message):
    await screen(m, "t_bad_check", Kb().add(B("b_cancel", "u:topup")))


# ---------------- Telegram Stars ----------------
@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    p = q.invoice_payload.split(":")
    ok = len(p) == 3 and p[0] == "st" and p[1] == str(q.from_user.id) and p[2].isdigit()
    await q.answer(ok=ok, error_message=None if ok else "To'lov ma'lumotlari noto'g'ri")


@router.message(F.successful_payment)
async def paid(m: Message, bot):
    sp = m.successful_payment
    p = sp.invoice_payload.split(":")
    uid, amount = m.from_user.id, int(p[2])
    _, rc = await db.x(
        "INSERT OR IGNORE INTO payments(user_id,method,amount,stars,status,charge_id,created_at) "
        "VALUES(?,?,?,?,?,?,?)", uid, "stars", amount, sp.total_amount, "approved",
        sp.telegram_payment_charge_id, db.now())
    if rc == 0:
        return
    bal = await credit(bot, uid, amount)
    await screen(m, "t_pay_ok", home_kb(), amount=fmt_money(amount), balance=fmt_money(bal))
    u = await get_user(uid)
    await notify_admins(bot, f"⭐ <b>Stars to'lov</b>\n👤 {esc(u['full_name'])} <code>{uid}</code>\n"
                             f"⭐ {sp.total_amount} Stars → {fmt_money(amount)}")
