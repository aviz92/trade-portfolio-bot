from custom_python_logger import get_logger
from python_custom_exceptions import BaseCustomException
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from trade_portfolio_bot.config import ALLOWED_TELEGRAM_USER_IDS
from trade_portfolio_bot.domain.cash import parse_deposit_command
from trade_portfolio_bot.domain.currency import CURRENCY_SYMBOLS, Currency
from trade_portfolio_bot.domain.trade import TradeSide, parse_trade_command

logger = get_logger(__name__)

BUY_USAGE = "<code>/buy TICKER QUANTITY PRICE</code>"
BUY_EXAMPLE = "<code>/buy AAPL 10 150.5</code>"
SELL_USAGE = "<code>/sell TICKER QUANTITY PRICE</code>"
SELL_EXAMPLE = "<code>/sell AAPL 5 160.0</code>"
DEPOSIT_USAGE = "<code>/deposit AMOUNT</code>"
DEPOSIT_EXAMPLE = "<code>/deposit 1000</code>"

BOT_COMMANDS = [
    BotCommand("buy", "Log a purchase — TICKER QUANTITY PRICE, then pick $ or ₪"),
    BotCommand("sell", "Log a sale — TICKER QUANTITY PRICE"),
    BotCommand("deposit", "Log cash added to your portfolio — AMOUNT, then pick $ or ₪"),
    BotCommand("whoami", "Show your Telegram user ID"),
    BotCommand("balance", "Show your cash balance"),
    BotCommand("reset", "Delete all your trades and deposits (asks to confirm)"),
    BotCommand("help", "Show usage and available commands"),
    BotCommand("start", "Show the welcome message"),
]

RESET_CALLBACK_PATTERN = r"^reset:(confirm|cancel):\d+$"
BUY_CURRENCY_CALLBACK_PATTERN = r"^buy:(USD|ILS|cancel):\d+$"
DEPOSIT_CURRENCY_CALLBACK_PATTERN = r"^deposit:(USD|ILS|cancel):\d+$"


def _currency_keyboard(prefix: str, user_id: int) -> InlineKeyboardMarkup:
    """Builds the $/₪/Cancel button row used by /buy and /deposit's currency prompts."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💵 $ Dollar", callback_data=f"{prefix}:USD:{user_id}"),
                InlineKeyboardButton("₪ ILS", callback_data=f"{prefix}:ILS:{user_id}"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"{prefix}:cancel:{user_id}")],
        ]
    )


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
        "/whoami — show your Telegram user ID\n"
        "/balance — show your cash balance\n"
        "/reset — delete all your trades and deposits (asks to confirm)\n\n"
        f"{DEPOSIT_USAGE}\n"
        "Log cash added to your portfolio — you'll be asked to pick $ or ₪.\n"
        f"Example: {DEPOSIT_EXAMPLE}\n\n"
        f"{BUY_USAGE}\n"
        "Log a purchase — you'll be asked to pick $ or ₪.\n"
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
    """Handles /buy TICKER QUANTITY PRICE — stages the trade and asks which currency it was in.
    Nothing is saved until the user picks a currency via the buttons."""
    try:
        trade = parse_trade_command(context.args or [], side=TradeSide.BUY)
    except BaseCustomException as e:
        logger.warning(f"Rejected /buy command: {e.message}", extra={"diagnostic_info": e.diagnostic_info})
        await update.effective_message.reply_html(
            f"⚠️ <b>{e.message}</b>\n\nUsage: {BUY_USAGE}\nExample: {BUY_EXAMPLE}"
        )
        return

    user_id = update.effective_user.id
    prompt = await update.effective_message.reply_html(
        "❔ <b>Which currency was this trade in?</b>\n\n"
        f"Ticker: <b>{trade.ticker}</b>\n"
        f"Qty:    {trade.quantity:g}\n"
        f"Price:  {trade.price:.2f}\n"
        f"Total:  <b>{trade.total_cost:.2f}</b>",
        reply_markup=_currency_keyboard("buy", user_id),
    )
    context.user_data["pending_trade"] = {"trade": trade, "message_id": prompt.message_id}


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /sell TICKER QUANTITY PRICE."""
    await _log_trade(update, context, TradeSide.SELL, SELL_USAGE, SELL_EXAMPLE)


async def buy_currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the $/₪/Cancel buttons from /buy — this is where the trade actually gets saved."""
    query = update.callback_query
    _, choice, raw_user_id = query.data.split(":")
    target_user_id = int(raw_user_id)

    if query.from_user.id != target_user_id:
        await query.answer("This confirmation isn't yours.", show_alert=True)
        return

    pending = context.user_data.get("pending_trade")
    if not pending or pending["message_id"] != query.message.message_id:
        await query.answer("This prompt has expired — send /buy again.", show_alert=True)
        return
    await query.answer()
    context.user_data.pop("pending_trade", None)

    if choice == "cancel":
        await query.edit_message_text("❌ Trade cancelled — nothing was logged.")
        return

    trade = pending["trade"]
    currency = Currency(choice)
    context.bot_data["repository"].save_trade(trade, user_id=target_user_id, currency=currency)
    logger.info(f"New trade logged: {trade} ({currency.value})")

    symbol = CURRENCY_SYMBOLS[currency]
    await query.edit_message_text(
        "✅ <b>Trade logged</b>\n\n"
        f"Side:    <b>{trade.side.value}</b>\n"
        f"Ticker:  <b>{trade.ticker}</b>\n"
        f"Qty:     {trade.quantity:g}\n"
        f"Price:   {symbol}{trade.price:.2f}\n"
        f"Total:   <b>{symbol}{trade.total_cost:.2f}</b>",
        parse_mode=ParseMode.HTML,
    )


async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /deposit AMOUNT — stages the deposit and asks which currency it was in.
    Nothing is saved until the user picks a currency via the buttons."""
    try:
        cash = parse_deposit_command(context.args or [])
    except BaseCustomException as e:
        logger.warning(f"Rejected /deposit command: {e.message}", extra={"diagnostic_info": e.diagnostic_info})
        await update.effective_message.reply_html(
            f"⚠️ <b>{e.message}</b>\n\nUsage: {DEPOSIT_USAGE}\nExample: {DEPOSIT_EXAMPLE}"
        )
        return

    user_id = update.effective_user.id
    prompt = await update.effective_message.reply_html(
        f"❔ <b>Which currency is this deposit in?</b>\n\nAmount: <b>{cash.amount:.2f}</b>",
        reply_markup=_currency_keyboard("deposit", user_id),
    )
    context.user_data["pending_deposit"] = {"cash": cash, "message_id": prompt.message_id}


async def deposit_currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the $/₪/Cancel buttons from /deposit — this is where the deposit actually gets saved."""
    query = update.callback_query
    _, choice, raw_user_id = query.data.split(":")
    target_user_id = int(raw_user_id)

    if query.from_user.id != target_user_id:
        await query.answer("This confirmation isn't yours.", show_alert=True)
        return

    pending = context.user_data.get("pending_deposit")
    if not pending or pending["message_id"] != query.message.message_id:
        await query.answer("This prompt has expired — send /deposit again.", show_alert=True)
        return
    await query.answer()
    context.user_data.pop("pending_deposit", None)

    if choice == "cancel":
        await query.edit_message_text("❌ Deposit cancelled — nothing was logged.")
        return

    cash = pending["cash"]
    currency = Currency(choice)
    context.bot_data["repository"].save_deposit(cash, user_id=target_user_id, currency=currency)
    logger.info(f"Cash deposit logged: {cash} ({currency.value})")

    symbol = CURRENCY_SYMBOLS[currency]
    await query.edit_message_text(
        f"✅ <b>Deposit logged</b>\n\nAmount: <b>{symbol}{cash.amount:.2f}</b>", parse_mode=ParseMode.HTML
    )


async def whoami(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /whoami — replies with the sender's Telegram user ID."""
    await update.effective_message.reply_html(f"🆔 Your Telegram user ID is <code>{update.effective_user.id}</code>.")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /balance — replies with the sender's cash balance and stock holdings."""
    repository = context.bot_data["repository"]
    user_id = update.effective_user.id
    cash_balances = repository.get_cash_balance(user_id)
    holdings = repository.get_holdings(user_id)

    cash_lines = (
        "\n".join(f"{CURRENCY_SYMBOLS[Currency(currency)]} {amount:.2f}" for currency, amount in cash_balances)
        or "(none)"
    )
    holdings_lines = "\n".join(f"{ticker}: {quantity:g} stocks" for ticker, quantity in holdings) or "(none)"

    await update.effective_message.reply_html(
        f"💰 <b>Cash</b>\n{cash_lines}\n\n"
        f"📈 <b>Stocks held</b> (quantity — no market value)\n{holdings_lines}"
    )


async def reset(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /reset — asks the sender to confirm before wiping their trades and deposits."""
    user_id = update.effective_user.id
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"reset:confirm:{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"reset:cancel:{user_id}"),
            ]
        ]
    )
    await update.effective_message.reply_html(
        "⚠️ <b>This deletes all your trades and cash deposits. This cannot be undone.</b>\n\nAre you sure?",
        reply_markup=keyboard,
    )


async def reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the Confirm/Cancel button presses from /reset."""
    query = update.callback_query
    _, action, raw_user_id = query.data.split(":")
    target_user_id = int(raw_user_id)

    if query.from_user.id != target_user_id:
        await query.answer("This confirmation isn't yours.", show_alert=True)
        return
    await query.answer()

    if action == "cancel":
        await query.edit_message_text("❌ Reset cancelled — nothing was deleted.")
        return

    context.bot_data["repository"].reset_user_data(target_user_id)
    logger.warning(f"Reset data for user_id={target_user_id}")
    await query.edit_message_text("✅ Your data has been reset — all trades and deposits deleted.")


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
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(reset_callback, pattern=RESET_CALLBACK_PATTERN))
    app.add_handler(CallbackQueryHandler(buy_currency_callback, pattern=BUY_CURRENCY_CALLBACK_PATTERN))
    app.add_handler(CallbackQueryHandler(deposit_currency_callback, pattern=DEPOSIT_CURRENCY_CALLBACK_PATTERN))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
