"""Admin: qo'llanmalar, yordam, majburiy obuna kanallari, xabar yuborish."""
import asyncio
import logging
import re

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import cache
import db
from handlers.admin_core import confirm_kb
from inputs import IsAdmin, ask, on_input
from ui import A, BK, Kb, esc, extract, premiumize, show

log = logging.getLogger(__name__)
router = Router(name="admin_content")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())
_tasks: set = set()
NAMES = {"guide": "Qo'llanmalar", "help": "Yordam bo'limi"}


# ================= qo'llanma / yordam =================
@router.callback_query(F.data.startswith("a:dl:"))
async def dl(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    kind = cb.data.split(":")[2]
    kb = Kb()
    for d in await db.q("SELECT id,title FROM docs WHERE kind=? ORDER BY id", kind):
        kb.add(A(f"📄 {d['title']}", f"a:d:{d['id']}"))
    kb.add(A("➕ Qo'shish", f"a:da:{kind}", "green")).add(BK("a:home"))
    await show(cb, f"{'📚' if kind == 'guide' else '🆘'} <b>{NAMES[kind]}</b>\n\n"
                   "Elementni tanlang yoki yangisini qo'shing. Har biriga matn, rasm, video yoki dumaloq video qo'yish mumkin.", kb)


async def doc_card(ev, did: int):
    d = await db.q1("SELECT * FROM docs WHERE id=?", did)
    if not d:
        return await show(ev, "Topilmadi", Kb().add(BK("a:home")))
    kb = Kb().add(A(f"📄 {d['title']}", "a:noop"))
    kb.add(A("✏️ Sarlavha", f"a:dt:{did}"), A("✏️ Matn", f"a:dx:{did}:text", "green"))
    kb.add(A("🖼 Media", f"a:dx:{did}:media", "blue"), A("🗑 Media", f"a:dm0:{did}"))
    kb.add(A("🗑 O'chirish", f"a:dd:{did}", "red"), BK(f"a:dl:{d['kind']}"))
    await show(ev, premiumize(d["text"] or "") or "<i>(matn yo'q)</i>", kb, d["media_type"], d["media_id"])


@router.callback_query(F.data.startswith("a:d:"))
async def d_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await doc_card(cb, int(cb.data.split(":")[2]))


@router.callback_query(F.data.startswith("a:da:"))
async def d_add(cb: CallbackQuery, state: FSMContext):
    kind = cb.data.split(":")[2]
    await ask(cb, state, "doc_title", "📝 Tugma uchun <b>sarlavha</b> yuboring:", f"a:dl:{kind}", kind=kind)


@on_input("doc_title")
async def d_title(m: Message, state: FSMContext, ctx: dict):
    if not m.text or len(m.text) > 50:
        return await m.answer("❌ Sarlavha yuboring (50 belgigacha).")
    await ask(m, state, "doc_new", "📄 Endi <b>matnni</b> yuboring.\n\nRasm/video/dumaloq video yuborsangiz ham bo'ladi "
              "(matn — izohda). Premium emoji va format qo'llab-quvvatlanadi.", f"a:dl:{ctx['kind']}",
              kind=ctx["kind"], title=m.text.strip())


@on_input("doc_new")
async def d_new(m: Message, state: FSMContext, ctx: dict):
    text, mt, mid = extract(m)
    if text is None and not mt:
        return await m.answer("❌ Matn yoki media yuboring.")
    did, _ = await db.x("INSERT INTO docs(kind,title,text,media_type,media_id,created_at) VALUES(?,?,?,?,?,?)",
                        ctx["kind"], ctx["title"], text, mt, mid, db.now())
    await state.clear()
    await doc_card(m, did)


@router.callback_query(F.data.startswith("a:dt:"))
async def d_edit_title(cb: CallbackQuery, state: FSMContext):
    did = cb.data.split(":")[2]
    await ask(cb, state, "doc_retitle", "✏️ Yangi sarlavhani yuboring:", f"a:d:{did}", id=int(did))


@on_input("doc_retitle")
async def d_retitle(m: Message, state: FSMContext, ctx: dict):
    if not m.text or len(m.text) > 50:
        return await m.answer("❌ Sarlavha yuboring (50 belgigacha).")
    await db.x("UPDATE docs SET title=? WHERE id=?", m.text.strip(), ctx["id"])
    await state.clear()
    await doc_card(m, ctx["id"])


@router.callback_query(F.data.startswith("a:dx:"))
async def d_edit_content(cb: CallbackQuery, state: FSMContext):
    _, _, did, mode = cb.data.split(":")
    p = "✏️ Yangi matnni yuboring (rasm/video + izoh ham mumkin):" if mode == "text" else \
        "🖼 Rasm, video, GIF yoki dumaloq video yuboring (izoh yozsangiz matn ham yangilanadi):"
    await ask(cb, state, "doc_recontent", p, f"a:d:{did}", id=int(did), mode=mode)


@on_input("doc_recontent")
async def d_recontent(m: Message, state: FSMContext, ctx: dict):
    text, mt, mid = extract(m)
    if (ctx["mode"] == "text" and text is None) or (ctx["mode"] == "media" and not mt):
        return await m.answer("❌ To'g'ri turdagi xabar yuboring.")
    if text is not None:
        await db.x("UPDATE docs SET text=? WHERE id=?", text, ctx["id"])
    if mt:
        await db.x("UPDATE docs SET media_type=?, media_id=? WHERE id=?", mt, mid, ctx["id"])
    await state.clear()
    await doc_card(m, ctx["id"])


@router.callback_query(F.data.startswith("a:dm0:"))
async def d_media_del(cb: CallbackQuery):
    did = int(cb.data.split(":")[2])
    await db.x("UPDATE docs SET media_type=NULL, media_id=NULL WHERE id=?", did)
    await doc_card(cb, did)


@router.callback_query(F.data.startswith("a:dd:"))
async def d_del(cb: CallbackQuery):
    did = cb.data.split(":")[2]
    await show(cb, "🗑 O'chirishni tasdiqlaysizmi?", confirm_kb(f"a:dd2:{did}", f"a:d:{did}"))


@router.callback_query(F.data.startswith("a:dd2:"))
async def d_del2(cb: CallbackQuery, state: FSMContext):
    d = await db.q1("SELECT kind FROM docs WHERE id=?", int(cb.data.split(":")[2]))
    await db.x("DELETE FROM docs WHERE id=?", int(cb.data.split(":")[2]))
    cb.data = f"a:dl:{d['kind'] if d else 'guide'}"
    await dl(cb, state)


# ================= majburiy obuna =================
@router.callback_query(F.data == "a:subs")
async def subs(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    on = cache.setting("sub_enabled", "1") == "1"
    kb = Kb().add(A(f"Majburiy obuna: {'✅ yoqilgan' if on else '🚫 o‘chiq'}", "a:chtog", "green" if on else "red"))
    for c in await db.q("SELECT * FROM channels ORDER BY id"):
        kb.add(A(f"{'✅' if c['active'] else '🚫'} {c['title'] or c['chat_id']}", f"a:ch:{c['id']}"))
    kb.add(A("➕ Kanal qo'shish", "a:chadd", "green")).add(BK("a:home"))
    await show(cb, "📢 <b>Majburiy obuna</b>\n\nBot qo'shilgan kanal/guruhda <b>admin</b> bo'lishi shart.", kb)


@router.callback_query(F.data == "a:chtog")
async def ch_toggle(cb: CallbackQuery, state: FSMContext):
    await cache.set_setting("sub_enabled", "0" if cache.setting("sub_enabled", "1") == "1" else "1")
    await subs(cb, state)


@router.callback_query(F.data == "a:chadd")
async def ch_add(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "ch_add", "📢 Kanaldan <b>xabarni forward qiling</b>, yoki <code>@username</code> / ID "
              "(<code>-100...</code>) yuboring.\n\nBot avval kanalga admin qilib qo'shilgan bo'lsin.", "a:subs")


async def _save_channel(m: Message, state: FSMContext, chat_id: int, title: str, link: str):
    await db.x("INSERT INTO channels(chat_id,title,link) VALUES(?,?,?)", chat_id, title, link)
    await state.clear()
    await m.answer("✅ Kanal qo'shildi.", reply_markup=Kb().add(A("📢 Ro'yxat", "a:subs", "green")).markup())


@on_input("ch_add")
async def ch_add_in(m: Message, state: FSMContext, ctx: dict):
    ident = None
    fo = m.forward_origin
    if fo is not None and getattr(fo, "chat", None) is not None:
        ident = fo.chat.id
    elif m.text:
        t = re.sub(r"^https?://t\.me/", "", m.text.strip())
        if t.lstrip("-").isdigit():
            ident = int(t)
        elif re.fullmatch(r"@?[A-Za-z0-9_]{4,}", t):
            ident = "@" + t.lstrip("@")
    if ident is None:
        return await m.answer("❌ Tushunmadim. Forward qiling yoki @username/ID yuboring.")
    try:
        chat = await m.bot.get_chat(ident)
        me = await m.bot.me()
        mem = await m.bot.get_chat_member(chat.id, me.id)
        if mem.status not in ("administrator", "creator"):
            return await m.answer("❌ Bot bu kanalda admin emas. Avval botni admin qiling.")
    except Exception as e:
        return await m.answer(f"❌ Kanal topilmadi yoki bot unda yo'q: {esc(e)}")
    link = f"https://t.me/{chat.username}" if chat.username else getattr(chat, "invite_link", None)
    if not link:
        try:
            link = await m.bot.export_chat_invite_link(chat.id)
        except Exception:
            link = None
    if not link:
        return await ask(m, state, "ch_link", "🔗 Kanal uchun taklif havolasini yuboring (https://t.me/+...):",
                         "a:subs", chat_id=chat.id, title=chat.title)
    await _save_channel(m, state, chat.id, chat.title, link)


@on_input("ch_link")
async def ch_link(m: Message, state: FSMContext, ctx: dict):
    if not m.text or not m.text.strip().startswith("http"):
        return await m.answer("❌ To'g'ri havola yuboring.")
    await _save_channel(m, state, ctx["chat_id"], ctx["title"], m.text.strip())


@router.callback_query(F.data.startswith("a:ch:"))
async def ch_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    cid = int(cb.data.split(":")[2])
    c = await db.q1("SELECT * FROM channels WHERE id=?", cid)
    if not c:
        return await subs(cb, state)
    kb = Kb().add(A("🚫 O'chirib qo'yish" if c["active"] else "✅ Yoqish", f"a:cht:{cid}", "blue"),
                  A("🗑 O'chirish", f"a:chd:{cid}", "red")).add(BK("a:subs"))
    await show(cb, f"📢 <b>{esc(c['title'])}</b>\n🆔 <code>{c['chat_id']}</code>\n🔗 {esc(c['link'])}", kb)


@router.callback_query(F.data.startswith("a:cht:"))
async def ch_tog(cb: CallbackQuery, state: FSMContext):
    await db.x("UPDATE channels SET active=1-active WHERE id=?", int(cb.data.split(":")[2]))
    await ch_open(cb, state)


@router.callback_query(F.data.startswith("a:chd:"))
async def ch_del(cb: CallbackQuery):
    cid = cb.data.split(":")[2]
    await show(cb, "🗑 Kanalni ro'yxatdan o'chirasizmi?", confirm_kb(f"a:chd2:{cid}", f"a:ch:{cid}"))


@router.callback_query(F.data.startswith("a:chd2:"))
async def ch_del2(cb: CallbackQuery, state: FSMContext):
    await db.x("DELETE FROM channels WHERE id=?", int(cb.data.split(":")[2]))
    await subs(cb, state)


# ================= xabar yuborish =================
@router.callback_query(F.data == "a:bc")
async def bc(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "bc", "📣 Barcha foydalanuvchilarga yuboriladigan xabarni yuboring "
              "(matn, rasm, video, premium emoji, tugmasiz).", "a:home")


@on_input("bc")
async def bc_in(m: Message, state: FSMContext, ctx: dict):
    n = (await db.q1("SELECT COUNT(*) c FROM users WHERE banned=0"))["c"]
    await state.set_state(None)
    await state.update_data(bc_chat=m.chat.id, bc_msg=m.message_id)
    await m.copy_to(m.chat.id)
    await m.answer(f"👆 Shu xabar <b>{n}</b> ta foydalanuvchiga yuboriladi. Tasdiqlaysizmi?",
                   reply_markup=confirm_kb("a:bcgo", "a:home").markup())


@router.callback_query(F.data == "a:bcgo")
async def bc_go(cb: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await state.clear()
    if "bc_msg" not in d:
        return await cb.answer("Xabar topilmadi", show_alert=True)
    await show(cb, "🚀 Yuborish boshlandi. Tugagach hisobot keladi.", Kb().add(BK("a:home")))
    t = asyncio.create_task(_broadcast(cb.bot, cb.from_user.id, d["bc_chat"], d["bc_msg"]))
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)


async def _broadcast(bot, admin_id: int, from_chat: int, msg_id: int):
    ok = fail = 0
    for r in await db.q("SELECT id FROM users WHERE banned=0"):
        for _ in range(2):
            try:
                await bot.copy_message(r["id"], from_chat, msg_id)
                ok += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
                continue
            except (TelegramForbiddenError, Exception):
                fail += 1
            break
        await asyncio.sleep(0.05)
    await bot.send_message(admin_id, f"📣 <b>Yuborish tugadi</b>\n\n✅ Yetkazildi: {ok}\n❌ Yetkazilmadi: {fail}")
