"""Admin: dizayn (tugmalar), matnlar (media bilan), premium emoji xaritasi."""
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import cache
from defaults import BUTTONS, TEXTS
from inputs import IsAdmin, ask, on_input
from ui import (A, BK, EMOJI_ANY, Kb, T, effective_button, ent_text, extract, safe_format, show, B)
from handlers.admin_core import confirm_kb

router = Router(name="admin_design")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

DOT = {"green": "🟢", "blue": "🔵", "red": "🔴"}
COLOR_NAME = {"green": "🟢 Yashil", "blue": "🔵 Ko'k", "red": "🔴 Qizil", "none": "⚪ Rangsiz"}


# ================= DIZAYN =================
@router.callback_query(F.data == "a:design")
async def design(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = Kb().add(A("✨ Premium emoji xaritasi", "a:emap", "green"))
    for k in BUTTONS:
        e = effective_button(k)
        kb.add(A(f"{DOT.get(e['style'], '⚪')} {safe_format(e['text'])}", f"a:bt:{k}"))
    kb.add(BK("a:home"))
    await show(cb, "🎨 <b>Dizayn</b>\n\nTugmani tanlang — matnini, rangini va premium emojisini o'zgartirasiz.\n\n"
                   "🟢 yashil  🔵 ko'k  🔴 qizil  ⚪ rangsiz", kb)


async def btn_card(ev, key: str):
    d, e = BUTTONS[key], effective_button(key)
    o = cache.buttons.get(key) or {}
    icon = o.get("emoji_id")
    icon_s = "o'chirilgan" if icon == "none" else (f"<code>{icon}</code>" if icon else "avto (xaritadan)")
    kb = Kb().add(B(key, "a:noop"))
    kb.add(A("✏️ Matnni o'zgartirish", f"a:btt:{key}"))
    kb.add(A("🟢 Yashil", f"a:btc:{key}:green", "green"), A("🔵 Ko'k", f"a:btc:{key}:blue", "blue"))
    kb.add(A("🔴 Qizil", f"a:btc:{key}:red", "red"), A("⚪ Rangsiz", f"a:btc:{key}:none"))
    kb.add(A("😀 Premium emoji qo'yish", f"a:bte:{key}", "green"))
    kb.add(A("🔄 Avto", f"a:bte1:{key}"), A("🚫 Emojisiz", f"a:bte0:{key}"))
    kb.add(A("♻️ Asl holatiga", f"a:btr:{key}", "red"), BK("a:design"))
    await show(ev, f"🎨 <b>{d.title}</b>\n\n📝 Matn: <code>{e['text']}</code>\n"
                   f"🎨 Rang: {COLOR_NAME[e['style'] or 'none']}\n😀 Premium emoji: {icon_s}\n\n"
                   f"👇 Foydalanuvchida shunday ko'rinadi:", kb)


@router.callback_query(F.data.startswith("a:bt:"))
async def bt_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await btn_card(cb, cb.data.split(":")[2])


@router.callback_query(F.data.startswith("a:btc:"))
async def bt_color(cb: CallbackQuery):
    _, _, key, color = cb.data.split(":")
    await cache.save_btn(key, style=color)
    await btn_card(cb, key)


@router.callback_query(F.data.startswith("a:bte0:"))
async def bt_noemoji(cb: CallbackQuery):
    key = cb.data.split(":")[2]
    await cache.save_btn(key, emoji_id="none")
    await btn_card(cb, key)


@router.callback_query(F.data.startswith("a:bte1:"))
async def bt_autoemoji(cb: CallbackQuery):
    key = cb.data.split(":")[2]
    await cache.save_btn(key, emoji_id=None)
    await btn_card(cb, key)


@router.callback_query(F.data.startswith("a:btr:"))
async def bt_reset(cb: CallbackQuery):
    key = cb.data.split(":")[2]
    await cache.reset_btn(key)
    await btn_card(cb, key)


@router.callback_query(F.data.startswith("a:btt:"))
async def bt_text(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[2]
    await ask(cb, state, "btn_text",
              "✏️ Tugma uchun yangi matn yuboring.\n\n💡 Matn boshiga <b>premium emoji</b> qo'ysangiz, u tugma "
              "ikonkasi bo'lib qoladi.\nO'zgaruvchilar (agar bor bo'lsa) o'zgarishsiz qoladi: "
              f"<code>{BUTTONS[key].text}</code>", f"a:bt:{key}", key=key)


@on_input("btn_text")
async def btn_text_in(m: Message, state: FSMContext, ctx: dict):
    if not m.text or len(m.text) > 60:
        return await m.answer("❌ Matn yuboring (60 belgigacha).")
    text, icon = m.text.strip(), cache.UNSET
    ents = m.entities or []
    if ents and ents[0].type == "custom_emoji" and ents[0].offset == 0:
        icon = ents[0].custom_emoji_id
        text = m.text[len(ent_text(m.text, ents[0])):].strip()
    if not text:
        return await m.answer("❌ Emojidan keyin matn ham yozing.")
    await cache.save_btn(ctx["key"], text=text, emoji_id=icon)
    await state.clear()
    await btn_card(m, ctx["key"])


@router.callback_query(F.data.startswith("a:bte:"))
async def bt_emoji(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[2]
    await ask(cb, state, "btn_emoji", "😀 <b>Premium emoji</b> yuboring (bitta xabarda bitta emoji).\n\n"
              "Yoki emoji ID raqamini yuboring.", f"a:bt:{key}", key=key)


@on_input("btn_emoji")
async def btn_emoji_in(m: Message, state: FSMContext, ctx: dict):
    eid = None
    for e in (m.entities or []):
        if e.type == "custom_emoji":
            eid = e.custom_emoji_id
            break
    if not eid and m.text and m.text.strip().isdigit() and len(m.text.strip()) > 10:
        eid = m.text.strip()
    if not eid:
        return await m.answer("❌ Premium emoji topilmadi. Premium emoji yuboring.")
    await cache.save_btn(ctx["key"], emoji_id=eid)
    await state.clear()
    await btn_card(m, ctx["key"])


# ================= PREMIUM EMOJI XARITASI =================
def _unmapped() -> str:
    used: list[str] = []
    for src in [b.text for b in BUTTONS.values()] + [t.text for t in TEXTS.values()]:
        for e in EMOJI_ANY.findall(src):
            n = cache.norm(e)
            if n not in used:
                used.append(n)
    miss = [e for e in used if e not in cache.emap]
    return " ".join(miss) if miss else "✅ hammasi qoplangan"


@router.callback_query(F.data == "a:emap")
async def emap(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = Kb().add(A("➕ Emoji paket / premium emoji yuborish", "a:emapi", "green"))
    kb.add(A("🗑 Xaritani tozalash", "a:emapc", "red")).add(BK("a:design"))
    await show(cb, f"✨ <b>Premium emoji xaritasi</b>\n\nHozir: <b>{len(cache.emap)}</b> ta emoji.\n\n"
                   "Bot oddiy emojilarni (🛒 💰 💎 ...) shu xarita bo'yicha <b>avtomatik premium emojiga</b> "
                   "almashtiradi — barcha tugma va matnlarda.\n\n<b>Qanday to'ldiriladi:</b>\n"
                   "1) Emoji paket havolasini yuboring (<code>t.me/addemoji/...</code>)\n"
                   "2) yoki bitta xabarda bir nechta premium emoji yuboring.\n\n"
                   f"Xaritada yo'q emojilar:\n{_unmapped()}\n\n"
                   "⚠️ Premium emoji ishlashi uchun bot egasida Telegram Premium bo'lishi kerak.", kb)


@router.callback_query(F.data == "a:emapi")
async def emap_ask(cb: CallbackQuery, state: FSMContext):
    await ask(cb, state, "emap", "✨ Emoji paket havolasini yoki premium emojilarni yuboring:", "a:emap")


@on_input("emap")
async def emap_in(m: Message, state: FSMContext, ctx: dict):
    added: dict[str, str] = {}
    for e in (m.entities or []):
        if e.type == "custom_emoji":
            added[cache.norm(ent_text(m.text, e))] = e.custom_emoji_id
    if not added and m.text:
        mt = re.search(r"addemoji/([A-Za-z0-9_]+)", m.text) or re.fullmatch(r"\s*([A-Za-z0-9_]{3,})\s*", m.text)
        if mt:
            try:
                st = await m.bot.get_sticker_set(mt.group(1))
                for s in st.stickers:
                    if s.custom_emoji_id and s.emoji:
                        added.setdefault(cache.norm(s.emoji), s.custom_emoji_id)
            except Exception as e:
                return await m.answer(f"❌ Paket topilmadi: {e}")
    if not added:
        return await m.answer("❌ Hech narsa topilmadi. Emoji paket havolasi yoki premium emoji yuboring.")
    await cache.add_emoji(added)
    await state.clear()
    await m.answer(f"✅ {len(added)} ta emoji xaritaga qo'shildi.",
                   reply_markup=Kb().add(A("✨ Xaritaga qaytish", "a:emap", "green")).markup())


@router.callback_query(F.data == "a:emapc")
async def emap_clear(cb: CallbackQuery):
    await show(cb, "🗑 Premium emoji xaritasi tozalansinmi?", confirm_kb("a:emapc2", "a:emap"))


@router.callback_query(F.data == "a:emapc2")
async def emap_clear2(cb: CallbackQuery, state: FSMContext):
    await cache.clear_emoji()
    await emap(cb, state)


# ================= MATNLAR =================
@router.callback_query(F.data == "a:texts")
async def texts(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = Kb()
    for k, d in TEXTS.items():
        o = cache.texts.get(k) or {}
        mark = ("✏️" if o.get("text") is not None else "") + ("🖼" if o.get("media_type") else "")
        kb.add(A(f"{mark + ' ' if mark else ''}{d.title}", f"a:tx:{k}"))
    kb.add(BK("a:home"))
    await show(cb, "✏️ <b>Matnlar</b>\n\nBotdagi barcha xabarlarni tahrirlash mumkin (matn, rasm, video, dumaloq video).\n"
                   "✏️ — matni o'zgartirilgan, 🖼 — media qo'yilgan.", kb)


async def text_card(ev, key: str):
    d = TEXTS[key]
    text, mt, mid = T(key, preview=True)
    kb = Kb().add(A("✏️ Matn", f"a:txe:{key}", "green"), A("🖼 Media", f"a:txm:{key}", "blue"))
    kb.add(A("🗑 Mediani o'chirish", f"a:txd:{key}"), A("♻️ Asl holat", f"a:txr:{key}", "red"))
    kb.add(BK("a:texts"))
    await show(ev, text, kb, mt, mid)
    # eslint: izoh xabari
    hint = f"👆 <b>{d.title}</b> — foydalanuvchiga shunday ko'rinadi (namuna ma'lumotlar bilan)."
    if d.vars:
        hint += f"\nO'zgaruvchilar: <code>{d.vars}</code>"
    await ev.bot.send_message(ev.from_user.id, hint)


@router.callback_query(F.data.startswith("a:tx:"))
async def tx_open(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await text_card(cb, cb.data.split(":")[2])


@router.callback_query(F.data.startswith("a:txe:"))
async def tx_edit(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[2]
    d = TEXTS[key]
    await ask(cb, state, "tx_content",
              f"✏️ <b>{d.title}</b>\n\nYangi matnni yuboring. Format (qalin, kursiv...) va <b>premium emoji</b> "
              f"qo'llab-quvvatlanadi.\n💡 Rasm/video + izoh yuborsangiz, matn ham, media ham o'rnatiladi.\n"
              f"O'zgaruvchilar: <code>{d.vars or '—'}</code>", f"a:tx:{key}", key=key, mode="text")


@router.callback_query(F.data.startswith("a:txm:"))
async def tx_media(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[2]
    await ask(cb, state, "tx_content", "🖼 <b>Rasm, video, GIF yoki dumaloq video</b> yuboring.\n\n"
              "Izoh (caption) yozsangiz, u xabar matniga aylanadi.", f"a:tx:{key}", key=key, mode="media")


@on_input("tx_content")
async def tx_content(m: Message, state: FSMContext, ctx: dict):
    text, mt, mid = extract(m)
    if ctx["mode"] == "text" and text is None:
        return await m.answer("❌ Matn yuboring.")
    if ctx["mode"] == "media" and not mt:
        return await m.answer("❌ Rasm, video, GIF yoki dumaloq video yuboring.")
    if text is not None:
        await cache.save_text(ctx["key"], text=text)
    if mt:
        await cache.save_text(ctx["key"], media_type=mt, media_id=mid)
    await state.clear()
    await text_card(m, ctx["key"])


@router.callback_query(F.data.startswith("a:txd:"))
async def tx_del_media(cb: CallbackQuery):
    key = cb.data.split(":")[2]
    if key in cache.texts:
        await cache.save_text(key, media_type=None, media_id=None)
    await text_card(cb, key)


@router.callback_query(F.data.startswith("a:txr:"))
async def tx_reset(cb: CallbackQuery):
    key = cb.data.split(":")[2]
    await cache.reset_text(key)
    await text_card(cb, key)
