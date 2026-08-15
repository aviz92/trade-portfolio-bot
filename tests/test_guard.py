from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.ext import ApplicationHandlerStop

from trade_portfolio_bot.bot.handlers import commands
from trade_portfolio_bot.db.repository import PortfolioRepository
from trade_portfolio_bot.domain.cash import CashDeposit
from trade_portfolio_bot.domain.trade import Trade, TradeSide


def _make_update(user_id, text="/buy AAPL 10 150.5"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.effective_message.text = text
    update.effective_message.reply_html = AsyncMock()
    return update


async def test_allowed_user_passes_through(monkeypatch):
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset({111}))
    update = _make_update(111)

    await commands.guard_allowed_users(update, MagicMock())

    update.effective_message.reply_html.assert_not_called()


async def test_non_allowed_user_is_rejected(monkeypatch):
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset({111}))
    update = _make_update(222)

    with pytest.raises(ApplicationHandlerStop):
        await commands.guard_allowed_users(update, MagicMock())

    update.effective_message.reply_html.assert_called_once()


async def test_empty_allowlist_lets_everyone_through(monkeypatch):
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset())
    update = _make_update(999)

    await commands.guard_allowed_users(update, MagicMock())

    update.effective_message.reply_html.assert_not_called()


async def test_whoami_bypasses_a_populated_allowlist(monkeypatch):
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset({111}))
    update = _make_update(222, text="/whoami")

    await commands.guard_allowed_users(update, MagicMock())

    update.effective_message.reply_html.assert_not_called()


async def test_whoami_with_bot_username_suffix_bypasses_allowlist(monkeypatch):
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset({111}))
    update = _make_update(222, text="/whoami@MyBot")

    await commands.guard_allowed_users(update, MagicMock())

    update.effective_message.reply_html.assert_not_called()


async def test_whoami_replies_with_the_sender_user_id():
    update = _make_update(222, text="/whoami")

    await commands.whoami(update, MagicMock())

    update.effective_message.reply_html.assert_called_once()
    assert "222" in update.effective_message.reply_html.call_args[0][0]


async def test_balance_replies_with_cash_and_no_holdings(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=222)

    update = _make_update(222, text="/balance")
    context = MagicMock()
    context.bot_data = {"repository": repo}

    await commands.balance(update, context)

    reply = update.effective_message.reply_html.call_args[0][0]
    assert "1000.00" in reply
    assert "(none)" in reply


async def test_balance_replies_with_cash_and_holdings(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=222)
    repo.save_trade(
        Trade(ticker="AAPL", side=TradeSide.BUY, quantity=10, price=150.5, timestamp=datetime.now(UTC)), user_id=222
    )

    update = _make_update(222, text="/balance")
    context = MagicMock()
    context.bot_data = {"repository": repo}

    await commands.balance(update, context)

    reply = update.effective_message.reply_html.call_args[0][0]
    assert "AAPL: 10 stocks" in reply
