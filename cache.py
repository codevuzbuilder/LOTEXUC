"""Xotiradagi kesh: sozlamalar, tugma/matn o'zgartirishlari, premium emoji xaritasi."""
import re
from defaults import SETTINGS

UNSET = object()
settings: dict[str, str] = {}
buttons: dict[str, dict] = {}
texts: dict[str, dict] = {}
emap: dict[str, str] = {}
admins_db: set[int] = set()
emoji_rx: re.Pattern | None = None


def norm(s: str) -> str:
    return s.replace("️", "")


def rebuild() -> None:
    global emoji_rx
    keys = sorted(emap, key=len, reverse=True)
    emoji_rx = (
        re.compile("(?:" + "|".join(re.escape(k) for k in keys) + ")️?") if keys else None
    )


async def load() -> None:
    settings.clear()
    settings.update({r["key"]: r["value"] for r in await db.q("SELECT * FROM settings")})
    buttons.clear()
    for r in await db.q("SELECT * FROM buttons"):
        buttons[r["key"]] = {"text": r["text"], "style": r["style"], "emoji_id": r["emoji_id"]}
    texts.clear()
    for r in await db.q("SELECT * FROM texts"):
        texts[r["key"]] = {
            "text": r["text"], "media_type": r["media_type"], "media_id": r["media_id"],
        }
    emap.clear()
    emap.update({r["char"]: r["emoji_id"] for r in await db.q("SELECT * FROM emoji_map")})
    rebuild()
    admins_db.clear()
    admins_db.update(r["id"] for r in await db.q("SELECT id FROM admins"))


def setting(key: str, default=None):
    v = settings.get(key)
    if v is None:
        v = SETTINGS.get(key, (None, None, None))[2]
    return default if v is None else v


def int_setting(key: str) -> int:
    try:
        return int(setting(key, 0))
    except (TypeError, ValueError):
        return 0


async def set_setting(key: str, value: str | None) -> None:
    if value is None:
        settings.pop(key, None)
        await db.x("DELETE FROM settings WHERE key=?", key)
    else:
        settings[key] = value
        await db.x(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", key, value)


async def save_btn(key: str, text=UNSET, style=UNSET, emoji_id=UNSET) -> None:
    row = dict(buttons.get(key) or {"text": None, "style": None, "emoji_id": None})
    if text is not UNSET:
        row["text"] = text
    if style is not UNSET:
        row["style"] = style
    if emoji_id is not UNSET:
        row["emoji_id"] = emoji_id
    buttons[key] = row
    await db.x(
        "INSERT INTO buttons(key,text,style,emoji_id) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE "
        "SET text=excluded.text, style=excluded.style, emoji_id=excluded.emoji_id",
        key, row["text"], row["style"], row["emoji_id"])


async def reset_btn(key: str) -> None:
    buttons.pop(key, None)
    await db.x("DELETE FROM buttons WHERE key=?", key)


async def save_text(key: str, text=UNSET, media_type=UNSET, media_id=UNSET) -> None:
    row = dict(texts.get(key) or {"text": None, "media_type": None, "media_id": None})
    if text is not UNSET:
        row["text"] = text
    if media_type is not UNSET:
        row["media_type"] = media_type
    if media_id is not UNSET:
        row["media_id"] = media_id
    texts[key] = row
    await db.x(
        "INSERT INTO texts(key,text,media_type,media_id) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE "
        "SET text=excluded.text, media_type=excluded.media_type, media_id=excluded.media_id",
        key, row["text"], row["media_type"], row["media_id"])


async def reset_text(key: str) -> None:
    texts.pop(key, None)
    await db.x("DELETE FROM texts WHERE key=?", key)


async def add_emoji(mapping: dict[str, str]) -> None:
    for ch, eid in mapping.items():
        emap[ch] = eid
        await db.x(
            "INSERT INTO emoji_map(char,emoji_id) VALUES(?,?) "
            "ON CONFLICT(char) DO UPDATE SET emoji_id=excluded.emoji_id", ch, eid)
    rebuild()


async def clear_emoji() -> None:
    emap.clear()
    await db.x("DELETE FROM emoji_map")
    rebuild()


async def add_admin(uid: int) -> None:
    admins_db.add(uid)
    await db.x("INSERT OR IGNORE INTO admins(id) VALUES(?)", uid)


async def remove_admin(uid: int) -> None:
    admins_db.discard(uid)
    await db.x("DELETE FROM admins WHERE id=?", uid)
