import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

import cache
import config
import db
import inputs
from handlers import admin_content, admin_core, admin_design, fallback, user
from middlewares import Core

log = logging.getLogger("bot")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not config.BOT_TOKEN:
        sys.exit("BOT_TOKEN topilmadi. .env faylini to'ldiring (.env.example ga qarang).")
    if not config.ADMIN_IDS:
        log.warning("ADMIN_IDS bo'sh! Admin panelga hech kim kira olmaydi.")
    await db.init(config.DB_PATH)
    await cache.load()

    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(Core())
    dp.callback_query.outer_middleware(Core())
    dp.include_routers(user.router, admin_core.router, admin_design.router, admin_content.router,
                       inputs.router, fallback.router)

    @dp.errors()
    async def on_error(ev: ErrorEvent):
        log.exception("Xatolik: %s", ev.exception)
        return True

    await bot.set_my_commands([BotCommand(command="start", description="Botni ishga tushirish"),
                               BotCommand(command="cancel", description="Bekor qilish")])
    await bot.delete_webhook(drop_pending_updates=False)
    log.info("Bot ishga tushdi: @%s", (await bot.me()).username)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())