from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.ext import ApplicationHandlerStop

from trade_portfolio_bot.bot.handlers import commands


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
