"""Interfeys: rangli tugmalar, premium emoji, matn/media yuborish."""
import html
import logging
import re
from dataclasses import dataclass

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import cache
from defaults import BUTTONS, SAMPLE, TEXTS

log = logging.getLogger(__name__)

STYLES = {"green": "success", "blue": "primary", "red": "danger"}

_EMOJI = (
    r"(?:[\U0001F000-\U0001FAFF←-⇿⌀-⏿①-➿⬀-⯿"
    r"©®‼⁉™ℹ]️?"
    r"(?:‍[\U0001F000-\U0001FAFF♀♂☀-➿⬀-⯿]️?)*)"
)
LEAD_RE = re.compile(rf"^\s*({_EMOJI}+)\s*")
EMOJI_ANY = re.compile(_EMOJI)
_SPLIT = re.compile(r"(<tg-emoji.*?</tg-emoji>|<[^>]*>)", re.S)
_PH = re.compile(r"\{(\w+)\}")
_TGE = re.compile(r"<tg-emoji[^>]*>(.*?)</tg-emoji>", re.S)


# ---------- formatlash ----------
def fmt_num(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def fmt_money(n) -> str:
    cur = cache.setting("currency", "so'm")
    return f"{fmt_num(n)} {cur}"


def esc(s) -> str:
    return html.escape(str(s or ""))


def safe_format(t: str, **kw) -> str:
    return _PH.sub(lambda m: str(kw[m.group(1)]) if m.group(1) in kw else m.group(0), t)


def parse_int(text: str | None) -> int | None:
    if not text:
        return None
    d = re.sub(r"[\s,._]", "", text)
    return int(d) if d.isdigit() else None


def ent_text(text: str, e) -> str:
    b = text.encode("utf-16-le")
    return b[e.offset * 2:(e.offset + e.length) * 2].decode("utf-16-le")


def extract(m: Message):
    """Xabardan (html_matn, media_turi, media_id) ni ajratadi."""
    mt = mid = None
    if m.photo:
        mt, mid = "photo", m.photo[-1].file_id
    elif m.video:
        mt, mid = "video", m.video.file_id
    elif m.animation:
        mt, mid = "animation", m.animation.file_id
    elif m.video_note:
        mt, mid = "video_note", m.video_note.file_id
    elif m.document:
        mt, mid = "document", m.document.file_id
    text = m.html_text if (m.text or m.caption) else None
    return text, mt, mid


# ---------- premium emoji ----------
def premiumize(text: str) -> str:
    """Oddiy emojilarni xaritadagi premium emojiga almashtiradi (HTML tegidan tashqarida)."""
    rx = cache.emoji_rx
    if not rx or not text:
        return text
    parts = _SPLIT.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = rx.sub(
            lambda m: f'<tg-emoji emoji-id="{cache.emap[cache.norm(m.group(0))]}">{m.group(0)}</tg-emoji>',
            parts[i])
    return "".join(parts)


def plain_text(t: str) -> str:
    return _TGE.sub(r"\1", t)


# ---------- tugmalar ----------
@dataclass
class Btn:
    text: str
    plain: str
    cb: str | None = None
    url: str | None = None
    style: str | None = None
    icon: str | None = None

    @classmethod
    def make(cls, text, cb=None, url=None, style=None, icon=None):
        plain = text
        m = LEAD_RE.match(text)
        if icon == "none":
            icon = None
        elif icon is None and m:
            icon = cache.emap.get(cache.norm(m.group(1)))
        if icon and m and text[m.end():]:
            text = text[m.end():]
        return cls(text, plain, cb, url, STYLES.get(style), icon)

    def to_tg(self, plain=False) -> InlineKeyboardButton:
        kw = {"text": self.plain if plain else self.text}
        if self.cb:
            kw["callback_data"] = self.cb
        if self.url:
            kw["url"] = self.url
        if self.style:
            kw["style"] = self.style
        if self.icon and not plain:
            kw["icon_custom_emoji_id"] = self.icon
        return InlineKeyboardButton(**kw)


class Kb:
    def __init__(self):
        self.rows: list[list[Btn]] = []

    def add(self, *btns: Btn) -> "Kb":
        self.rows.append(list(btns))
        return self

    def markup(self, plain=False):
        if not self.rows:
            return None
        return InlineKeyboardMarkup(inline_keyboard=[[b.to_tg(plain) for b in r] for r in self.rows])

    @property
    def has_icons(self) -> bool:
        return any(b.icon for r in self.rows for b in r)


def effective_button(key: str) -> dict:
    d = BUTTONS[key]
    o = cache.buttons.get(key) or {}
    style = o.get("style") or d.style
    if style == "none":
        style = None
    return {"text": o.get("text") or d.text, "style": style, "icon": o.get("emoji_id")}


def B(key: str, cb=None, url=None, **fmt) -> Btn:
    e = effective_button(key)
    return Btn.make(safe_format(e["text"], **fmt), cb, url, e["style"], e["icon"])


def A(text: str, cb=None, style=None, url=None) -> Btn:
    """Admin paneli uchun oddiy (qat'iy) tugma."""
    return Btn.make(text, cb, url, style)


def BK(cb: str) -> Btn:
    return A("⬅️ Orqaga", cb)


# ---------- matnlar ----------
def T(key: str, preview=False, **vars):
    d = TEXTS[key]
    o = cache.texts.get(key) or {}
    text = o.get("text") if o.get("text") is not None else d.text
    v = {**SAMPLE, **vars} if preview else vars
    return premiumize(safe_format(text, **v)), o.get("media_type"), o.get("media_id")


# ---------- yuborish ----------
_SEND = {"photo": "send_photo", "video": "send_video", "animation": "send_animation",
         "document": "send_document"}


async def _attempt(fn, text: str, kb: Kb | None):
    mk = kb.markup() if kb else None
    try:
        return await fn(text, mk)
    except TelegramBadRequest as e:
        if not ("<tg-emoji" in text or (kb and kb.has_icons)):
            raise
        log.warning("Premium emoji ishlamadi, oddiy ko'rinishda qayta yuborilmoqda: %s", e)
        return await fn(plain_text(text), kb.markup(plain=True) if kb else None)


async def send_fresh(bot, chat_id, text, kb: Kb | None = None, mt=None, mid=None):
    text = text or ""

    def msg(t, mk):
        return bot.send_message(chat_id, t or "…", reply_markup=mk)

    if mt == "video_note":
        if text:
            await bot.send_video_note(chat_id, mid)
            return await _attempt(msg, text, kb)
        return await _attempt(lambda t, mk: bot.send_video_note(chat_id, mid, reply_markup=mk), "", kb)
    if mt in _SEND:
        send = getattr(bot, _SEND[mt])
        if len(text) > 1000:
            await send(chat_id, mid)
            return await _attempt(msg, text, kb)
        return await _attempt(
            lambda t, mk: send(chat_id, mid, caption=t or None, reply_markup=mk), text, kb)
    return await _attempt(msg, text, kb)


async def show(ev, text: str, kb: Kb | None = None, mt=None, mid=None):
    """Ekranni ko'rsatadi: callback bo'lsa joyida tahrirlaydi, bo'lmasa yangi xabar yuboradi."""
    if isinstance(ev, Message):
        return await send_fresh(ev.bot, ev.chat.id, text, kb, mt, mid)
    msg = ev.message
    if not isinstance(msg, Message):
        return await send_fresh(ev.bot, ev.from_user.id, text, kb, mt, mid)
    if mt is None and msg.text is not None:
        try:
            return await _attempt(lambda t, mk: msg.edit_text(t or "…", reply_markup=mk), text, kb)
        except TelegramBadRequest as e:
            if "not modified" in str(e):
                return msg
    try:
        await msg.delete()
    except Exception:
        pass
    return await send_fresh(ev.bot, msg.chat.id, text, kb, mt, mid)


async def screen(ev, key: str, kb: Kb | None = None, **vars):
    text, mt, mid = T(key, **vars)
    return await show(ev, text, kb, mt, mid)
