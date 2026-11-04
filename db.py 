import time
from pathlib import Path

import aiosqlite

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
  balance INTEGER NOT NULL DEFAULT 0, referrer_id INTEGER,
  ref_rewarded INTEGER NOT NULL DEFAULT 0, ref_earned INTEGER NOT NULL DEFAULT 0,
  banned INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ix_users_ref ON users(referrer_id);
CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS buttons(key TEXT PRIMARY KEY, text TEXT, style TEXT, emoji_id TEXT);
CREATE TABLE IF NOT EXISTS texts(key TEXT PRIMARY KEY, text TEXT, media_type TEXT, media_id TEXT);
CREATE TABLE IF NOT EXISTS emoji_map(char TEXT PRIMARY KEY, emoji_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS packages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, uc INTEGER NOT NULL, price INTEGER NOT NULL,
  active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, uc INTEGER NOT NULL,
  price INTEGER NOT NULL, player_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  created_at INTEGER NOT NULL, done_at INTEGER);
CREATE INDEX IF NOT EXISTS ix_orders_user ON orders(user_id);
CREATE TABLE IF NOT EXISTS payments(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, method TEXT NOT NULL,
  amount INTEGER NOT NULL, stars INTEGER, status TEXT NOT NULL, charge_id TEXT UNIQUE,
  file_id TEXT, file_type TEXT, created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ix_pay_user ON payments(user_id);
CREATE TABLE IF NOT EXISTS channels(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, title TEXT, link TEXT,
  active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS docs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, title TEXT NOT NULL,
  text TEXT, media_type TEXT, media_id TEXT, created_at INTEGER);
"""


def now() -> int:
    return int(time.time())


async def init(path: str) -> None:
    global _db
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.executescript(SCHEMA)
    await _db.commit()


async def q(sql: str, *p):
    async with _db.execute(sql, p) as c:
        return await c.fetchall()


async def q1(sql: str, *p):
    async with _db.execute(sql, p) as c:
        return await c.fetchone()


async def x(sql: str, *p) -> tuple[int, int]:
    """(lastrowid, rowcount)"""
    c = await _db.execute(sql, p)
    await _db.commit()
    return c.lastrowid, c.rowcount