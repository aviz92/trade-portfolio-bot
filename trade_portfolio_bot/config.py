import os

from custom_python_logger import build_logger
from dotenv import load_dotenv

load_dotenv()

if not (TELEGRAM_BOT_TOKEN := os.getenv("TELEGRAM_BOT_TOKEN", "")):
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in your .env file")

DATABASE_PATH = os.getenv("DATABASE_PATH", "trade_portfolio_bot.db")

ALLOWED_TELEGRAM_USER_IDS = frozenset(
    int(user_id) for user_id in os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").split(",") if user_id.strip()
)

build_logger(project_name="trade-portfolio-bot")
