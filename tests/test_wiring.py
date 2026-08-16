from collections.abc import AsyncIterator
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from telegram import Bot, CallbackQuery, Chat, Message, MessageEntity, Update, User as TgUser
from telegram.ext import Application

from trade_portfolio_bot.bot.handlers import commands
from trade_portfolio_bot.db.repository import PortfolioRepository
from trade_portfolio_bot.domain.trade import Trade, TradeSide

FAKE_BOT_USER = TgUser(id=999, first_name="TestBot", is_bot=True, username="TestBot")


def _seed_trade(repository: PortfolioRepository, user_id: int) -> None:
    """Seeds a trade directly, bypassing the /buy confirm flow — used by tests that only care
    about /reset behavior, not about how the trade got there."""
    repository.save_trade(
        Trade(ticker="AAPL", side=TradeSide.BUY, quantity=10, price=150.5, timestamp=datetime.now(UTC)),
        user_id=user_id,
    )


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
    # Persists on the app across multiple _dispatch calls within one test, so message_ids grow
    # monotonically like real Telegram ones — needed for /buy and /deposit's stale-prompt check.
    seq = app.bot_data.setdefault("_test_msg_seq", count(1))

    async def fake_send_message(*args: object, **kwargs: object) -> Message:
        reply_text = kwargs.get("text") or (args[1] if len(args) > 1 else None)
        sent.append(reply_text)
        return Message(
            message_id=next(seq), date=datetime.now(UTC), chat=Chat(id=user_id, type=Chat.PRIVATE), text=reply_text
        )

    with patch.object(type(app.bot), "send_message", AsyncMock(side_effect=fake_send_message)):
        update = _build_update(app.bot, update_id=1, user_id=user_id, text=text, edited=edited)
        await app.process_update(update)

    return sent


def _build_callback_update(
    bot: Bot, update_id: int, clicking_user_id: int, callback_data: str, message_id: int | None = None
) -> Update:
    # The message the buttons are attached to; buttons are always sent to the user who ran the
    # original command, but clicking_user_id can differ to simulate someone else tapping them.
    chat = Chat(id=clicking_user_id, type=Chat.PRIVATE)
    from_user = TgUser(id=clicking_user_id, first_name="Test", is_bot=False)
    original_message = Message(
        message_id=message_id if message_id is not None else update_id,
        date=datetime.now(UTC),
        chat=chat,
        from_user=from_user,
    )
    original_message.set_bot(bot)
    callback_query = CallbackQuery(
        id=str(update_id), from_user=from_user, chat_instance="ci", message=original_message, data=callback_data
    )
    callback_query.set_bot(bot)
    return Update(update_id=update_id, callback_query=callback_query)


async def _dispatch_callback(
    app: Application, clicking_user_id: int, callback_data: str, message_id: int | None = None
) -> str | None:
    edited_text = None

    async def fake_edit_message_text(*args: object, **kwargs: object) -> None:
        nonlocal edited_text
        edited_text = kwargs.get("text") or (args[1] if len(args) > 1 else None)

    with (
        patch.object(type(app.bot), "answer_callback_query", AsyncMock(return_value=True)),
        patch.object(type(app.bot), "edit_message_text", AsyncMock(side_effect=fake_edit_message_text)),
    ):
        update = _build_callback_update(
            app.bot,
            update_id=2,
            clicking_user_id=clicking_user_id,
            callback_data=callback_data,
            message_id=message_id,
        )
        await app.process_update(update)

    return edited_text


async def test_buy_command_dispatches_through_real_application(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    sent = await _dispatch(application, 111, "/buy AAPL 10 150.5")

    assert len(sent) == 1
    assert "Which currency" in sent[0]
    # Nothing is saved until the currency is confirmed via the buttons.
    assert application.bot_data["repository"].get_holdings(111) == []


async def test_buy_confirm_with_usd_saves_the_trade(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    repository = application.bot_data["repository"]
    await _dispatch(application, 111, "/buy AAPL 10 150.5")

    edited_text = await _dispatch_callback(application, clicking_user_id=111, callback_data="buy:USD:111", message_id=1)

    assert edited_text is not None
    assert "Trade logged" in edited_text
    assert "$150.50" in edited_text
    assert repository.get_holdings(111) == [("AAPL", 10.0)]


async def test_buy_cancel_does_not_save_the_trade(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    repository = application.bot_data["repository"]
    await _dispatch(application, 111, "/buy AAPL 10 150.5")

    edited_text = await _dispatch_callback(
        application, clicking_user_id=111, callback_data="buy:cancel:111", message_id=1
    )

    assert edited_text is not None
    assert "cancelled" in edited_text.lower()
    assert repository.get_holdings(111) == []


async def test_buy_confirm_from_a_stale_prompt_is_rejected(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    """A second /buy before the first is confirmed replaces the pending trade; tapping the
    first (now stale) prompt's button must not silently log the wrong trade."""
    repository = application.bot_data["repository"]
    await _dispatch(application, 111, "/buy AAPL 10 150.5")  # message_id 1, now stale
    await _dispatch(application, 111, "/buy MSFT 5 300")  # message_id 2, current pending

    edited_text = await _dispatch_callback(application, clicking_user_id=111, callback_data="buy:USD:111", message_id=1)

    assert edited_text is None
    assert repository.get_holdings(111) == []


async def test_buy_confirm_from_a_different_user_is_rejected(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    repository = application.bot_data["repository"]
    await _dispatch(application, 111, "/buy AAPL 10 150.5")

    edited_text = await _dispatch_callback(application, clicking_user_id=222, callback_data="buy:USD:111", message_id=1)

    assert edited_text is None
    assert repository.get_holdings(111) == []


async def test_deposit_confirm_with_ils_saves_the_deposit(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    repository = application.bot_data["repository"]
    sent = await _dispatch(application, 111, "/deposit 1000")
    assert "Which currency" in sent[0]
    assert repository.get_cash_balance(111) == []

    edited_text = await _dispatch_callback(
        application, clicking_user_id=111, callback_data="deposit:ILS:111", message_id=1
    )

    assert edited_text is not None
    assert "Deposit logged" in edited_text
    assert "₪1000.00" in edited_text
    assert repository.get_cash_balance(111) == [("ILS", 1000.0)]


async def test_deposit_cancel_does_not_save(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    repository = application.bot_data["repository"]
    await _dispatch(application, 111, "/deposit 1000")

    edited_text = await _dispatch_callback(
        application, clicking_user_id=111, callback_data="deposit:cancel:111", message_id=1
    )

    assert edited_text is not None
    assert "cancelled" in edited_text.lower()
    assert repository.get_cash_balance(111) == []


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
    assert "Which currency" in sent[0]


async def test_reset_command_sends_confirmation_prompt(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    sent_kwargs = {}

    async def fake_send_message(*args: object, **kwargs: object) -> None:
        sent_kwargs.update(kwargs)

    with patch.object(type(application.bot), "send_message", AsyncMock(side_effect=fake_send_message)):
        update = _build_update(application.bot, update_id=1, user_id=111, text="/reset")
        await application.process_update(update)

    assert "cannot be undone" in sent_kwargs["text"]
    buttons = sent_kwargs["reply_markup"].inline_keyboard[0]
    assert [b.callback_data for b in buttons] == ["reset:confirm:111", "reset:cancel:111"]
    assert application.bot_data["repository"].get_holdings(111) == []


async def test_reset_confirm_deletes_the_users_data(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    repository = application.bot_data["repository"]
    _seed_trade(repository, 111)
    assert repository.get_holdings(111) == [("AAPL", 10.0)]

    edited_text = await _dispatch_callback(application, clicking_user_id=111, callback_data="reset:confirm:111")

    assert edited_text is not None
    assert "reset" in edited_text.lower()
    assert repository.get_holdings(111) == []


async def test_reset_cancel_keeps_the_users_data(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    repository = application.bot_data["repository"]
    _seed_trade(repository, 111)

    edited_text = await _dispatch_callback(application, clicking_user_id=111, callback_data="reset:cancel:111")

    assert edited_text is not None
    assert "cancelled" in edited_text.lower()
    assert repository.get_holdings(111) == [("AAPL", 10.0)]


async def test_reset_confirm_from_a_different_user_is_rejected(
    application: Application,  # pylint: disable=redefined-outer-name
) -> None:
    """The buttons carry the intended user_id; someone else tapping them must not trigger a
    delete of the original user's data."""
    repository = application.bot_data["repository"]
    _seed_trade(repository, 111)

    edited_text = await _dispatch_callback(application, clicking_user_id=222, callback_data="reset:confirm:111")

    assert edited_text is None
    assert repository.get_holdings(111) == [("AAPL", 10.0)]
