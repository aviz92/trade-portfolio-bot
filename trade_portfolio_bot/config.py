import os

from custom_python_logger import build_logger
from dotenv import load_dotenv

load_dotenv()

if not (TELEGRAM_BOT_TOKEN := os.getenv("TELEGRAM_BOT_TOKEN", "")):
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in your .env file")

build_logger(project_name="trade-portfolio-bot")
