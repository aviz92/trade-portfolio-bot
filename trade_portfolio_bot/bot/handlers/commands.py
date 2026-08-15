from custom_python_logger import get_logger
from python_custom_exceptions import BaseCustomException
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from trade_portfolio_bot.config import ALLOWED_TELEGRAM_USER_IDS
from trade_portfolio_bot.domain.cash import parse_deposit_command
from trade_portfolio_bot.domain.trade import TradeSide, parse_trade_command

logger = get_logger(__name__)

BUY_USAGE = "<code>/buy TICKER QUANTITY PRICE</code>"
BUY_EXAMPLE = "<code>/buy AAPL 10 150.5</code>"
SELL_USAGE = "<code>/sell TICKER QUANTITY PRICE</code>"
SELL_EXAMPLE = "<code>/sell AAPL 5 160.0</code>"
DEPOSIT_USAGE = "<code>/deposit AMOUNT</code>"
DEPOSIT_EXAMPLE = "<code>/deposit 1000</code>"

BOT_COMMANDS = [
    BotCommand("buy", "Log a purchase — TICKER QUANTITY PRICE"),
    BotCommand("sell", "Log a sale — TICKER QUANTITY PRICE"),
    BotCommand("deposit", "Log cash added to your portfolio — AMOUNT"),
    BotCommand("whoami", "Show your Telegram user ID"),
    BotCommand("help", "Show usage and available commands"),
    BotCommand("start", "Show the welcome message"),
]


def _is_whoami_command(update: Update) -> bool:
    if not (text := update.effective_message.text if update.effective_message else None):
        return False
    return text.split()[0].split("@")[0] == "/whoami"


async def guard_allowed_users(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Blocks non-allowlisted users before any command handler runs."""
    # /whoami stays open so a locked-down bot can still onboard new users onto the allowlist.
    if not ALLOWED_TELEGRAM_USER_IDS or _is_whoami_command(update):
        return
    if update.effective_user and update.effective_user.id in ALLOWED_TELEGRAM_USER_IDS:
        return

    user_id = update.effective_user.id if update.effective_user else None
    logger.warning(f"Rejected message from non-allowed user_id={user_id}")
    await update.effective_message.reply_html("⛔ <b>You're not authorized to use this bot.</b>")
    raise ApplicationHandlerStop


async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sent when user types /start."""
    user = update.effective_user
    await update.effective_message.reply_html(
        f"👋 <b>Welcome, {user.first_name}!</b>\n\n"
        "I track your portfolio's securities purchases and sales.\n\n"
        "<b>Get started</b>\n"
        f"{BUY_USAGE}\n"
        f"Example: {BUY_EXAMPLE}\n\n"
        "Send /help anytime for the full command list."
    )


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sent when user types /help."""
    await update.effective_message.reply_html(
        "<b>📖 Available commands</b>\n\n"
        "/start — show the welcome message\n"
        "/help — show this message\n"
        "/whoami — show your Telegram user ID\n\n"
        f"{DEPOSIT_USAGE}\n"
        "Log cash added to your portfolio.\n"
        f"Example: {DEPOSIT_EXAMPLE}\n\n"
        f"{BUY_USAGE}\n"
        "Log a purchase.\n"
        f"Example: {BUY_EXAMPLE}\n\n"
        f"{SELL_USAGE}\n"
        "Log a sale.\n"
        f"Example: {SELL_EXAMPLE}"
    )


async def _log_trade(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    side: TradeSide,
    usage: str,
    example: str,
) -> None:
    """Parses a /buy or /sell command, logs the trade, and confirms to the user."""
    try:
        trade = parse_trade_command(context.args or [], side=side)
    except BaseCustomException as e:
        logger.warning(
            f"Rejected /{side.value.lower()} command: {e.message}", extra={"diagnostic_info": e.diagnostic_info}
        )
        await update.effective_message.reply_html(f"⚠️ <b>{e.message}</b>\n\nUsage: {usage}\nExample: {example}")
        return

    context.bot_data["repository"].save_trade(trade, user_id=update.effective_user.id)
    logger.info(f"New trade logged: {trade}")

    await update.effective_message.reply_html(
        "✅ <b>Trade logged</b>\n\n"
        f"Side:    <b>{trade.side.value}</b>\n"
        f"Ticker:  <b>{trade.ticker}</b>\n"
        f"Qty:     {trade.quantity:g}\n"
        f"Price:   {trade.price:.2f}\n"
        f"Total:   <b>{trade.total_cost:.2f}</b>"
    )


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /buy TICKER QUANTITY PRICE."""
    await _log_trade(update, context, TradeSide.BUY, BUY_USAGE, BUY_EXAMPLE)


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /sell TICKER QUANTITY PRICE."""
    await _log_trade(update, context, TradeSide.SELL, SELL_USAGE, SELL_EXAMPLE)


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /deposit AMOUNT — logs cash added to the portfolio."""
    try:
        cash = parse_deposit_command(context.args or [])
    except BaseCustomException as e:
        logger.warning(f"Rejected /deposit command: {e.message}", extra={"diagnostic_info": e.diagnostic_info})
        await update.effective_message.reply_html(
            f"⚠️ <b>{e.message}</b>\n\nUsage: {DEPOSIT_USAGE}\nExample: {DEPOSIT_EXAMPLE}"
        )
        return

    context.bot_data["repository"].save_deposit(cash, user_id=update.effective_user.id)
    logger.info(f"Cash deposit logged: {cash}")

    await update.effective_message.reply_html(f"✅ <b>Deposit logged</b>\n\nAmount: <b>{cash.amount:.2f}</b>")


async def whoami(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /whoami — replies with the sender's Telegram user ID."""
    await update.effective_message.reply_html(f"🆔 Your Telegram user ID is <code>{update.effective_user.id}</code>.")


async def unknown_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches any /command that isn't registered above."""
    await update.effective_message.reply_html(
        f"❓ Unrecognized command: <code>{update.effective_message.text}</code>\n\nSend /help to see available commands."
    )


def register_command_handlers(app: Application) -> None:
    app.add_handler(MessageHandler(filters.ALL, guard_allowed_users), group=-1)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("sell", sell))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
