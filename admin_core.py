"""Admin: bosh panel, sozlamalar, statistika, adminlar, UC paketlari, buyurtmalar, to'lovlar, foydalanuvchilar."""
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import cache
import config
import db
from defaults import SETTINGS
from inputs import IsAdmin, ask, on_input
from services import credit, get_user, notify_user, uvars
from ui import A, BK, Kb, esc, fmt_money, parse_int, show

router = Router(name="admin_core")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

OST = {"pending": "⏳", "done": "✅", "canceled": "❌", "approved": "✅", "rejected": "❌"}


def confirm_kb(yes: str, no: str) -> Kb:
    return Kb().add(A("✅ Ha", yes, "green"), A("❌ Yo'q", no, "red"))


async def mark(cb: CallbackQuery, suffix: str, kb: Kb | None = None):
    msg = cb.message
    new = (msg.html_text or "") + f"\n\n{suffix}"
    try:
        if msg.text:
            await msg.edit_text(new, reply_markup=kb.markup() if kb else None)
        else:
            await msg.edit_caption(caption=new, reply_markup=kb.markup() if kb else None)
    except TelegramBadRequest:
        pass


# ================= bosh panel =================
async def admin_home(ev, state: FSMContext):
    await state.clear()
    po = (await db.q1("SELECT COUNT(*) c FROM orders WHERE status='pending'"))["c"]
    pp = (await db.q1("SELECT COUNT(*) c FROM payments WHERE status='pending'"))["c"]
    nu = (await db.q1("SELECT COUNT(*) c FROM users"))["c"]
    kb = Kb()
    kb.add(A("💎 UC paketlari", "a:pkgs", "green"), A("🎨 Dizayn", "a:design", "blue"))
    kb.add(A("✏️ Matnlar", "a:texts"), A("📢 Majburiy obuna", "a:subs"))
    kb.add(A("📚 Qo'llanmalar", "a:dl:guide"), A("🆘 Yordam bo'limi", "a:dl:help"))
    kb.add(A(f"📦 Buyurtmalar ({po})", "a:orders", "green"), A(f"🧾 To'lovlar ({pp})", "a:pays", "green"))
    kb.add(A("👥 Foydalanuvchilar", "a:users"), A("📣 Xabar yuborish", "a:bc"))
    kb.add(A("⚙️ Sozlamalar", "a:set"), A("📊 Statistika", "a:stats"))
    kb.add(A("👮 Adminlar", "a:admins"), A("🏠 Foydalanuvchi menyusi", "home", "red"))
    await show(ev, f"⚙️ <b>Admin panel</b>\n\n👥 Foydalanuvchilar: <b>{nu}</b>\n"
                   f"⏳ Kutilayotgan buyurtmalar: <b>{po}</b>\n⏳ Kutilayotgan to'lovlar: <b>{pp}</b>", kb)


@router.message(Command("admin"))
async def cmd_admin(m: Message, state: FSMContext):
    await admin_home(m, state)


@router.callback_query(F.data == "a:home")
async def cb_admin(cb: CallbackQuery, state: FSMContext):
    await admin_home(cb, state)


@router.callback_query(F.data == "a:noop")
async def noop(cb: CallbackQuery):
    await cb.answer()


# ================= sozlamalar =================
def _val(key: str) -> str:
    kind = SETTINGS[key][1]
    v = cache.settings.get(key, SETTINGS[key][2])
    if kind == "bool":
        return "✅ yoqilgan" if v == "1" else "🚫 o'chiq"
    if v in (None, ""):
        return "— kiritilmagan"
    return fmt_money(v) if kind == "int" and key != "stars_rate" else str(v)


async def settings_screen(ev, state: FSMContext):
    await state.clear()
    kb = Kb()
    for k, (title, kind, _) in SETTINGS.items():
        kb.add(A(f"{title}: {_val(k)}", f"a:s:{k}", "green" if kind == "bool" else None))
    kb.add(BK("a:home"))
    await show(ev, "⚙️ <b>Sozlamalar</b>\n\nO'zgartirish uchun tugmani bosing.\n"
                   "Matnli qiymatni o'chirish uchun <code>-</code> yuboring.", kb)


@router.callback_query(F.data == "a:set")
async def set_menu(cb: CallbackQuery, state: FSMContext):
    await settings_screen(cb, state)


@router.callback_query(F.data.startswith("a:s:"))
async def set_edit(cb: CallbackQuery, state: FSMContext):
    key = cb.data[4:]
    if key not in SETTINGS:
        return
    title, kind, _ = SETTINGS[key]
    if kind == "bool":
        cur = cache.setting(key, "0")
        await cache.set_setting(key, "0" if cur == "1" else "1")
        return await settings_screen(cb, state)
    hint = "raqam" if kind == "int" else "matn"
    await ask(cb, state, "set_val", f"✏️ <b>{title}</b>\n\nHozir: {_val(key)}\n\nYangi qiymatni yuboring ({hint}):",
              "a:set", key=key)


@on_input("set_val")
async def set_val(m: Message, state: FSMContext, ctx: dict):
    key = ctx["key"]
    kind = SETTINGS[key][1]
    t = (m.text or "").strip()
    if not t:
        return await m.answer("❌ Matn yuboring.")
    if t == "-":
        await cache.set_setting(key, None)
    elif kind == "int":
        n = parse_int(t)
        if n is None or (key == "stars_rate" and n < 1):
            return await m.answer("❌ Faqat musbat raqam yuboring.")
        await cache.set_setting(key, str(n))
    else:
        if key == "support":
            t = t.replace("https://t.me/", "").lstrip("@")
        await cache.set_setting(key, t)
    await settings_screen(m, state)


# ================= statistika =================
@router.callback_query(F.data == "a:stats")
async def stats(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    day = db.now() - 86400
    one = lambda sql, *p: db.q1(sql, *p)  # noqa: E731
    users = (await one("SELECT COUNT(*) c FROM users"))["c"]
    new = (await one("SELECT COUNT(*) c FROM users WHERE created_at>=?", day))["c"]
    bal = (await one("SELECT COALESCE(SUM(balance),0) s FROM users"))["s"]
    o = {r["status"]: (r["c"], r["s"]) for r in await db.q(
        "SELECT status, COUNT(*) c, COALESCE(SUM(price),0) s FROM orders GROUP BY status")}
    p = {r["method"]: (r["c"], r["s"]) for r in await db.q(
        "SELECT method, COUNT(*) c, COALESCE(SUM(amount),0) s FROM payments WHERE status='approved' GROUP BY method")}
    g = lambda d, k: d.get(k, (0, 0))  # noqa: E731
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users}</b> (24 soatda +{new})\n💰 Jami balanslar: <b>{fmt_money(bal)}</b>\n\n"
        f"📦 Buyurtmalar:\n  ⏳ {g(o, 'pending')[0]} • ✅ {g(o, 'done')[0]} • ❌ {g(o, 'canceled')[0]}\n"
        f"  💵 Bajarilgan summa: <b>{fmt_money(g(o, 'done')[1])}</b>\n\n"
        f"🧾 Tasdiqlangan to'lovlar:\n  ⭐ Stars: {g(p, 'stars')[0]} ta — {fmt_money(g(p, 'stars')[1])}\n"
        f"  💳 Karta: {g(p, 'manual')[0]} ta — {fmt_money(g(p, 'manual')[1])}")
    await show(cb, text, Kb().add(BK("a:home")))


# ================= adminlar =================
@router.callback_query(F.data == "a:admins")
async def admins(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    if cb.from_user.id not in config.ADMIN_IDS:
        return await cb.answer("Faqat asosiy adminlar uchun", show_alert=True)
    kb = Kb()
    lines = [f"👑 <code>{i}</code> (asosiy)" for i in sorted(config.ADMIN_IDS)]
    for i in sorted(cache.admins_db):
        lines.append(f"👮 <code>{i}</code>")
        kb.add(A(f"🗑 {i}", f"a:admd:{i}", "red"))
    kb.add(A("➕ Admin qo'shish", "a:adma", "green")).add(BK("a:home"))
    await show(cb, "👮 <b>Adminlar</b>\n\n" + "\n".join(lines), kb)


@router.callback_query(F.data == "a:adma")
async def adm_add(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id in config.ADMIN_IDS:
        await ask(cb, state, "adm_add", "👮 Yangi adminning Telegram ID raqamini yuboring:", "a:admins")


@on_input("adm_add")
async def adm_add_in(m: Message, state: FSMContext, ctx: dict):
    n = parse_int(m.text)
    if not n:
        return await m.answer("❌ Faqat ID raqam yuboring.")
    await cache.add_admin(n)
    await state.clear()
    await m.answer(f"✅ <code>{n}</code> admin qilindi. Admin botga /start bosgan bo'lishi kerak.",
                   reply_markup=Kb().add(BK("a:admins")).markup())


@router.callback_query(F.data.startswith("a:admd:"))
async def adm_del(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id in config.ADMIN_IDS:
        await cache.remove_admin(int(cb.data.split(":")[2]))
        await admins(cb, state)


# ================= UC paketlari =================
@router.callback_query(F.data == "a:pkgs")
async def pkgs(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    rows = await db.q("SELECT * FROM packages ORDER BY uc")
    kb = Kb()
    for r in rows:
        kb.add(A(f"{'✅' if r['active'] else '🚫'} {r['uc']} UC — {fmt_money(r['price'])}", f"a:pk:{r['id']}"))
    kb.add(A("➕ UC paketi qo'shish", "a:pkadd", "green")).add(BK("a:home"))
    note = "" if rows else "\n\nHozircha paket yo'q. «➕» tugmasi bilan UC soni va narxini kiriting."
    await show(cb, f"💎 <b>UC paketlari</b>{note}", kb)


async def pkg_card(ev, pid: int):
    p = await db.q1("SELECT * FROM packages WHERE id=?", pid)
    if not p:
        return await show(ev, "Topilmadi", Kb().add(BK("a:pkgs")))
    kb = Kb()
    kb.add(A("✏️ UC soni", f"a:pke:uc:{pid}"), A("✏️ Narxi", f"a:pke:price:{pid}"))
    kb.add(A("🚫 O'chirib qo'yish" if p["active"] else "✅ Yoqish", f"a:pkt:{pid}", "blue"),
           A("🗑 O'chirish", f"a:pkd:{pid}", "red"))
    kb.add(BK("a:pkgs"))
    await show(ev, f"💎 <b>UC paketi</b>\n\nUC: <b>{p['uc']}</b>\nNarxi: <b>{fmt_money(p['price'])}</b>\n"
                   f"Holati: {'✅ faol' if p['active'] else '🚫 o‘chiq'}", kb)


@router.callback_query(F.data.startswith("a:pk:"))
async def pk_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await pkg_card(cb, int(cb.data.split(":")[2]))


@router.callback_query(F.data == "a:pkadd")
async def pk_add(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "pk_add_uc", "💎 UC sonini yuboring (masalan: 60):", "a:pkgs")


@on_input("pk_add_uc")
async def pk_add_uc(m: Message, state: FSMContext, ctx: dict):
    n = parse_int(m.text)
    if not n:
        return await m.answer("❌ Faqat raqam yuboring.")
    await ask(m, state, "pk_add_price", f"💵 <b>{n} UC</b> narxini yuboring ({cache.setting('currency')}):",
              "a:pkgs", uc=n)


@on_input("pk_add_price")
async def pk_add_price(m: Message, state: FSMContext, ctx: dict):
    n = parse_int(m.text)
    if not n:
        return await m.answer("❌ Faqat raqam yuboring.")
    pid, _ = await db.x("INSERT INTO packages(uc,price) VALUES(?,?)", ctx["uc"], n)
    await state.clear()
    await pkg_card(m, pid)


@router.callback_query(F.data.startswith("a:pke:"))
async def pk_edit(cb: CallbackQuery, state: FSMContext):
    _, _, field, pid = cb.data.split(":")
    label = "UC sonini" if field == "uc" else "narxini"
    await ask(cb, state, "pk_edit", f"✏️ Yangi {label} yuboring:", f"a:pk:{pid}", field=field, id=int(pid))


@on_input("pk_edit")
async def pk_edit_in(m: Message, state: FSMContext, ctx: dict):
    n = parse_int(m.text)
    if not n:
        return await m.answer("❌ Faqat raqam yuboring.")
    col = "uc" if ctx["field"] == "uc" else "price"
    await db.x(f"UPDATE packages SET {col}=? WHERE id=?", n, ctx["id"])
    await state.clear()
    await pkg_card(m, ctx["id"])


@router.callback_query(F.data.startswith("a:pkt:"))
async def pk_toggle(cb: CallbackQuery):
    pid = int(cb.data.split(":")[2])
    await db.x("UPDATE packages SET active=1-active WHERE id=?", pid)
    await pkg_card(cb, pid)


@router.callback_query(F.data.startswith("a:pkd:"))
async def pk_del(cb: CallbackQuery):
    pid = cb.data.split(":")[2]
    await show(cb, "🗑 Bu paketni o'chirishni tasdiqlaysizmi?", confirm_kb(f"a:pkd2:{pid}", f"a:pk:{pid}"))


@router.callback_query(F.data.startswith("a:pkd2:"))
async def pk_del2(cb: CallbackQuery, state: FSMContext):
    await db.x("DELETE FROM packages WHERE id=?", int(cb.data.split(":")[2]))
    await pkgs(cb, state)


# ================= buyurtmalar =================
async def order_text(o) -> str:
    u = await get_user(o["user_id"])
    return (f"📦 <b>Buyurtma №{o['id']}</b> {OST[o['status']]}\n\n👤 {esc(u['full_name'])} "
            f"(<a href=\"tg://user?id={u['id']}\">{u['id']}</a>)\n💎 <b>{o['uc']} UC</b> — {fmt_money(o['price'])}\n"
            f"🎮 PUBG ID: <code>{esc(o['player_id'])}</code>\n🕒 {time.strftime('%d.%m.%Y %H:%M', time.gmtime(o['created_at'] + 18000))}")


def order_kb(o) -> Kb:
    kb = Kb()
    if o["status"] == "pending":
        kb.add(A("✅ Bajarildi", f"ao:done:{o['id']}", "green"), A("❌ Bekor qilish", f"ao:cancel:{o['id']}", "red"))
    return kb.add(BK(f"a:ol:{o['status']}"))


@router.callback_query(F.data == "a:orders")
async def orders(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    c = {r["status"]: r["c"] for r in await db.q("SELECT status, COUNT(*) c FROM orders GROUP BY status")}
    kb = Kb().add(A(f"⏳ Kutilayotgan ({c.get('pending', 0)})", "a:ol:pending", "green"))
    kb.add(A(f"✅ Bajarilgan ({c.get('done', 0)})", "a:ol:done"), A(f"❌ Bekor ({c.get('canceled', 0)})", "a:ol:canceled"))
    await show(cb, "📦 <b>Buyurtmalar</b>", kb.add(BK("a:home")))


@router.callback_query(F.data.startswith("a:ol:"))
async def order_list(cb: CallbackQuery):
    st = cb.data.split(":")[2]
    rows = await db.q("SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT 20", st)
    kb = Kb()
    for r in rows:
        kb.add(A(f"№{r['id']} • {r['uc']} UC • ID {r['player_id']}", f"a:o:{r['id']}"))
    await show(cb, f"📦 <b>Buyurtmalar</b> {OST[st]} (oxirgi 20 ta)" + ("" if rows else "\n\nBo'sh."), kb.add(BK("a:orders")))


@router.callback_query(F.data.startswith("a:o:"))
async def order_open(cb: CallbackQuery):
    o = await db.q1("SELECT * FROM orders WHERE id=?", int(cb.data.split(":")[2]))
    if o:
        await show(cb, await order_text(o), order_kb(o))


@router.callback_query(F.data.startswith("ao:"))
async def order_action(cb: CallbackQuery, bot):
    _, act, oid = cb.data.split(":")
    o = await db.q1("SELECT * FROM orders WHERE id=?", int(oid))
    if not o or o["status"] != "pending":
        return await cb.answer("Bu buyurtma allaqachon ko'rib chiqilgan", show_alert=True)
    who = f"({esc(cb.from_user.full_name)})"
    v = dict(order_id=o["id"], uc=o["uc"], price=fmt_money(o["price"]), player_id=esc(o["player_id"]))
    if act == "done":
        _, rc = await db.x("UPDATE orders SET status='done', done_at=? WHERE id=? AND status='pending'", db.now(), o["id"])
        if rc:
            await notify_user(bot, o["user_id"], "t_order_done", **v)
            await mark(cb, f"✅ <b>Bajarildi</b> {who}")
    elif act == "cancel":
        await show(cb, f"❌ Buyurtma №{oid} bekor qilinib, <b>{fmt_money(o['price'])}</b> foydalanuvchiga "
                       f"qaytariladi. Tasdiqlaysizmi?", confirm_kb(f"ao:cancel2:{oid}", f"a:o:{oid}"))
    elif act == "cancel2":
        _, rc = await db.x("UPDATE orders SET status='canceled' WHERE id=? AND status='pending'", o["id"])
        if rc:
            await db.x("UPDATE users SET balance=balance+? WHERE id=?", o["price"], o["user_id"])
            bal = (await get_user(o["user_id"]))["balance"]
            await notify_user(bot, o["user_id"], "t_order_cancel", **v, balance=fmt_money(bal))
            await mark(cb, f"❌ <b>Bekor qilindi, pul qaytarildi</b> {who}")


# ================= to'lovlar =================
@router.callback_query(F.data == "a:pays")
async def pays(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    c = {r["status"]: r["c"] for r in await db.q("SELECT status, COUNT(*) c FROM payments GROUP BY status")}
    kb = Kb().add(A(f"⏳ Kutilayotgan ({c.get('pending', 0)})", "a:pl:pending", "green"))
    kb.add(A(f"✅ Tasdiqlangan ({c.get('approved', 0)})", "a:pl:approved"), A(f"❌ Rad ({c.get('rejected', 0)})", "a:pl:rejected"))
    await show(cb, "🧾 <b>To'lovlar</b>", kb.add(BK("a:home")))


@router.callback_query(F.data.startswith("a:pl:"))
async def pay_list(cb: CallbackQuery):
    st = cb.data.split(":")[2]
    rows = await db.q("SELECT * FROM payments WHERE status=? ORDER BY id DESC LIMIT 20", st)
    kb = Kb()
    for r in rows:
        kb.add(A(f"№{r['id']} • {'⭐' if r['method'] == 'stars' else '💳'} {fmt_money(r['amount'])}", f"a:p:{r['id']}"))
    await show(cb, f"🧾 <b>To'lovlar</b> {OST[st]} (oxirgi 20 ta)" + ("" if rows else "\n\nBo'sh."), kb.add(BK("a:pays")))


@router.callback_query(F.data.startswith("a:p:"))
async def pay_open(cb: CallbackQuery):
    p = await db.q1("SELECT * FROM payments WHERE id=?", int(cb.data.split(":")[2]))
    if not p:
        return
    u = await get_user(p["user_id"])
    kb = Kb()
    if p["status"] == "pending":
        kb.add(A("✅ Tasdiqlash", f"ap:ok:{p['id']}", "green"), A("❌ Rad etish", f"ap:no:{p['id']}", "red"))
    kb.add(BK(f"a:pl:{p['status']}"))
    text = (f"🧾 <b>To'lov №{p['id']}</b> {OST[p['status']]}\n\n👤 {esc(u['full_name'])} <code>{u['id']}</code>\n"
            f"💵 {fmt_money(p['amount'])}\n{'⭐ ' + str(p['stars']) + ' Stars' if p['method'] == 'stars' else '💳 Karta'}")
    await show(cb, text, kb, p["file_type"], p["file_id"])


@router.callback_query(F.data.startswith("ap:"))
async def pay_action(cb: CallbackQuery, bot):
    _, act, pid = cb.data.split(":")
    p = await db.q1("SELECT * FROM payments WHERE id=?", int(pid))
    new = "approved" if act == "ok" else "rejected"
    if not p or p["method"] != "manual":
        return await cb.answer("Topilmadi", show_alert=True)
    _, rc = await db.x("UPDATE payments SET status=? WHERE id=? AND status='pending'", new, p["id"])
    if not rc:
        return await cb.answer("Bu so'rov allaqachon ko'rib chiqilgan", show_alert=True)
    who = f"({esc(cb.from_user.full_name)})"
    if act == "ok":
        bal = await credit(bot, p["user_id"], p["amount"])
        await notify_user(bot, p["user_id"], "t_pay_ok", amount=fmt_money(p["amount"]), balance=fmt_money(bal))
        await mark(cb, f"✅ <b>Tasdiqlandi</b> {who}")
    else:
        await notify_user(bot, p["user_id"], "t_pay_rejected", pay_id=p["id"])
        await mark(cb, f"❌ <b>Rad etildi</b> {who}")


# ================= foydalanuvchilar =================
@router.callback_query(F.data == "a:users")
async def users(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    n = (await db.q1("SELECT COUNT(*) c FROM users"))["c"]
    kb = Kb().add(A("🔎 ID / @username bo'yicha qidirish", "a:ufind", "green"))
    kb.add(A("🆕 So'nggi foydalanuvchilar", "a:ulast")).add(BK("a:home"))
    await show(cb, f"👥 <b>Foydalanuvchilar:</b> {n}", kb)


@router.callback_query(F.data == "a:ulast")
async def ulast(cb: CallbackQuery):
    kb = Kb()
    for r in await db.q("SELECT id, full_name FROM users ORDER BY created_at DESC, id DESC LIMIT 15"):
        kb.add(A(f"{r['full_name'] or r['id']} • {r['id']}", f"a:u:{r['id']}"))
    await show(cb, "🆕 <b>So'nggi foydalanuvchilar</b>", kb.add(BK("a:users")))


@router.callback_query(F.data == "a:ufind")
async def ufind(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "u_find", "🔎 Foydalanuvchi ID raqami yoki @username yuboring:", "a:users")


@on_input("u_find")
async def u_find(m: Message, state: FSMContext, ctx: dict):
    t = (m.text or "").strip()
    u = await (get_user(int(t)) if t.isdigit() else db.q1("SELECT * FROM users WHERE username=?", t.lstrip("@")))
    if not u:
        return await m.answer("❌ Topilmadi. Qayta yuboring.")
    await state.clear()
    await user_card(m, u["id"])


async def user_card(ev, uid: int):
    u = await get_user(uid)
    o = (await db.q1("SELECT COUNT(*) c FROM orders WHERE user_id=?", uid))["c"]
    r = (await db.q1("SELECT COUNT(*) c FROM users WHERE referrer_id=?", uid))["c"]
    kb = Kb().add(A("➕ Balans qo'shish", f"a:ub:add:{uid}", "green"), A("➖ Ayirish", f"a:ub:sub:{uid}", "red"))
    kb.add(A("✅ Banni olish" if u["banned"] else "🚫 Ban qilish", f"a:uban:{uid}", "blue"),
           A("💬 Profil", url=f"tg://user?id={uid}"))
    kb.add(BK("a:users"))
    await show(ev, f"👤 <b>{esc(u['full_name'])}</b>\n🆔 <code>{uid}</code>\n🔗 @{u['username'] or '—'}\n"
                   f"💰 Balans: <b>{fmt_money(u['balance'])}</b>\n📦 Buyurtmalar: {o}\n👥 Takliflar: {r}\n"
                   f"🚫 Ban: {'ha' if u['banned'] else 'yo‘q'}", kb)


@router.callback_query(F.data.startswith("a:u:"))
async def u_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await user_card(cb, int(cb.data.split(":")[2]))


@router.callback_query(F.data.startswith("a:uban:"))
async def u_ban(cb: CallbackQuery):
    uid = int(cb.data.split(":")[2])
    await db.x("UPDATE users SET banned=1-banned WHERE id=?", uid)
    await user_card(cb, uid)


@router.callback_query(F.data.startswith("a:ub:"))
async def u_bal(cb: CallbackQuery, state: FSMContext):
    _, _, op, uid = cb.data.split(":")
    await ask(cb, state, "u_bal", f"💰 {'Qo‘shiladigan' if op == 'add' else 'Ayiriladigan'} summani yuboring:",
              f"a:u:{uid}", op=op, uid=int(uid))


@on_input("u_bal")
async def u_bal_in(m: Message, state: FSMContext, ctx: dict):
    n = parse_int(m.text)
    if not n:
        return await m.answer("❌ Faqat musbat raqam yuboring.")
    uid = ctx["uid"]
    if ctx["op"] == "add":
        await credit(m.bot, uid, n, reward_ref=False)
        delta = "+" + fmt_money(n)
    else:
        _, rc = await db.x("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?", n, uid, n)
        if not rc:
            return await m.answer("❌ Foydalanuvchi balansi yetarli emas.")
        delta = "−" + fmt_money(n)
    await state.clear()
    u = await get_user(uid)
    await notify_user(m.bot, uid, "t_bal_adj", delta=delta, balance=fmt_money(u["balance"]))
    await user_card(m, uid)
