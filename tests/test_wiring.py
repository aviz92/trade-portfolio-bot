from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from telegram import Bot, Chat, Message, MessageEntity, Update, User as TgUser
from telegram.ext import Application

from trade_portfolio_bot.bot.handlers import commands
from trade_portfolio_bot.db.repository import PortfolioRepository

FAKE_BOT_USER = TgUser(id=999, first_name="TestBot", is_bot=True, username="TestBot")


async def _fake_get_me(self: Bot, **_kwargs: object) -> TgUser:
    # Real get_me() hits the network and caches the result on self._bot_user; this stub
    # skips the network call but preserves that caching so CommandHandler's real matching
    # logic (which reads message.get_bot().username) works unmodified.
    self._bot_user = FAKE_BOT_USER  # pylint: disable=protected-access
    return FAKE_BOT_USER


def _command_entities(text: str) -> list[MessageEntity]:
    if not text.startswith("/"):
        return []
    return [MessageEntity(type=MessageEntity.BOT_COMMAND, offset=0, length=len(text.split()[0]))]


def _build_update(bot: Bot, update_id: int, user_id: int, text: str, edited: bool = False) -> Update:
    chat = Chat(id=user_id, type=Chat.PRIVATE)
    user = TgUser(id=user_id, first_name="Test", is_bot=False)
    message = Message(
        message_id=update_id,
        date=datetime.now(UTC),
        chat=chat,
        from_user=user,
        text=text,
        entities=_command_entities(text),
    )
    message.set_bot(bot)
    if edited:
        return Update(update_id=update_id, edited_message=message)
    return Update(update_id=update_id, message=message)


@pytest.fixture
async def application(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Application]:
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset())
    repository = PortfolioRepository(tmp_path / "wiring.db")
    app = Application.builder().token("123456:FAKE-TOKEN-FOR-TESTS").build()
    app.bot_data["repository"] = repository
    commands.register_command_handlers(app)

    with patch.object(type(app.bot), "get_me", _fake_get_me):
        await app.initialize()

    yield app

    await app.shutdown()
    repository.close()


async def _dispatch(app: Application, user_id: int, text: str, edited: bool = False) -> list[str]:
    sent: list[str] = []

    async def fake_send_message(*args: object, **kwargs: object) -> None:
        sent.append(kwargs.get("text") or (args[1] if len(args) > 1 else None))

    with patch.object(type(app.bot), "send_message", AsyncMock(side_effect=fake_send_message)):
        update = _build_update(app.bot, update_id=1, user_id=user_id, text=text, edited=edited)
        await app.process_update(update)

    return sent


async def test_buy_command_dispatches_through_real_application(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    sent = await _dispatch(application, 111, "/buy AAPL 10 150.5")

    assert len(sent) == 1
    assert "Trade logged" in sent[0]
    assert application.bot_data["repository"].get_holdings(111) == [("AAPL", 10.0)]


async def test_unknown_command_falls_through_to_the_catch_all(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    sent = await _dispatch(application, 111, "/frobnicate")

    assert len(sent) == 1
    assert "Unrecognized command" in sent[0]


async def test_guard_blocks_non_allowed_user_through_real_dispatch(
    application: Application,  # pylint: disable=redefined-outer-name
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset({111}))

    sent = await _dispatch(application, 222, "/buy AAPL 10 150.5")

    assert sent == ["⛔ <b>You're not authorized to use this bot.</b>"]
    assert application.bot_data["repository"].get_holdings(222) == []


async def test_whoami_bypasses_lockdown_through_real_dispatch(
    application: Application,  # pylint: disable=redefined-outer-name
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(commands, "ALLOWED_TELEGRAM_USER_IDS", frozenset({111}))

    sent = await _dispatch(application, 222, "/whoami")

    assert len(sent) == 1
    assert "222" in sent[0]


async def test_edited_message_command_still_gets_a_reply(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    """Regression: CommandHandler matches on update.effective_message, which covers edited
    messages too. Early code read update.message directly instead, which is None for an
    edited message and crashed with AttributeError on .reply_html."""
    sent = await _dispatch(application, 111, "/buy AAPL 10 150.5", edited=True)

    assert len(sent) == 1
    assert "Trade logged" in sent[0]
