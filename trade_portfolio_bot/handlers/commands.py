from custom_python_logger import get_logger
from python_custom_exceptions import BaseCustomException
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from trade_portfolio_bot.trade import parse_buy_command

logger = get_logger(__name__)

BUY_USAGE = "<code>/buy TICKER QUANTITY PRICE</code>"
BUY_EXAMPLE = "<code>/buy AAPL 10 150.5</code>"

BOT_COMMANDS = [
    BotCommand("buy", "Log a purchase — TICKER QUANTITY PRICE"),
    BotCommand("help", "Show usage and available commands"),
    BotCommand("start", "Show the welcome message"),
]


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sent when user types /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"👋 <b>Welcome, {user.first_name}!</b>\n\n"
        "I track your portfolio's securities purchases.\n\n"
        "<b>Get started</b>\n"
        f"{BUY_USAGE}\n"
        f"Example: {BUY_EXAMPLE}\n\n"
        "Send /help anytime for the full command list."
    )


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sent when user types /help."""
    await update.message.reply_html(
        "<b>📖 Available commands</b>\n\n"
        f"{BUY_USAGE}\n"
        "Log a purchase.\n"
        f"Example: {BUY_EXAMPLE}\n\n"
        "/start — show the welcome message\n"
        "/help — show this message"
    )


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /buy TICKER QUANTITY PRICE — logs the trade and confirms to the user."""
    try:
        trade = parse_buy_command(context.args or [])
    except BaseCustomException as e:
        logger.warning(f"Rejected /buy command: {e.message}", extra={"diagnostic_info": e.diagnostic_info})
        await update.message.reply_html(f"⚠️ <b>{e.message}</b>\n\nUsage: {BUY_USAGE}\nExample: {BUY_EXAMPLE}")
        return

    logger.info(f"New trade logged: {trade}")

    await update.message.reply_html(
        "✅ <b>Trade logged</b>\n\n"
        f"Ticker:  <b>{trade.ticker}</b>\n"
        f"Qty:     {trade.quantity:g}\n"
        f"Price:   {trade.price:.2f}\n"
        f"Total:   <b>{trade.total_cost:.2f}</b>"
    )


async def unknown_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches any /command that isn't registered above."""
    await update.message.reply_html(
        f"❓ Unrecognized command: <code>{update.message.text}</code>\n\nSend /help to see available commands."
    )


def register_command_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
