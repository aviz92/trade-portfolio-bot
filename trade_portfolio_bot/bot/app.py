from custom_python_logger import get_logger
from telegram import Update
from telegram.ext import Application, ContextTypes

from trade_portfolio_bot.bot.handlers.commands import BOT_COMMANDS, register_command_handlers
from trade_portfolio_bot.config import DATABASE_PATH, TELEGRAM_BOT_TOKEN
from trade_portfolio_bot.db.repository import PortfolioRepository

logger = get_logger(__name__)


async def error_handler(_update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception:", exc_info=context.error)


async def post_init(app: Application) -> None:
    """Registers the command menu shown in Telegram's chat UI."""
    await app.bot.set_my_commands(BOT_COMMANDS)


async def post_shutdown(app: Application) -> None:
    """Closes the SQLite connection when the bot stops."""
    app.bot_data["repository"].close()


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    app.bot_data["repository"] = PortfolioRepository(DATABASE_PATH)

    register_command_handlers(app)
    app.add_error_handler(error_handler)

    logger.info("trade-portfolio-bot is running... Press Ctrl-C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
