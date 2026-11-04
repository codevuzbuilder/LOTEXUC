import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
# .env dagi adminlar — "super adminlar" (boshqa adminlarni qo'sha oladi)
ADMIN_IDS: set[int] = {
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
}
DB_PATH = os.getenv("DB_PATH", "data/bot.db")