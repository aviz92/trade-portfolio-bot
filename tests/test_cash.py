import pytest

from trade_portfolio_bot.domain.cash import parse_deposit_command
from trade_portfolio_bot.domain.exceptions import InvalidAmountException, InvalidCashCommandException


def test_parse_deposit_command_valid() -> None:
    cash = parse_deposit_command(["1000"])
    assert cash.amount == 1000


def test_parse_deposit_command_wrong_arg_count() -> None:
    with pytest.raises(InvalidCashCommandException):
        parse_deposit_command(["1000", "extra"])


def test_parse_deposit_command_non_numeric_amount() -> None:
    with pytest.raises(InvalidAmountException):
        parse_deposit_command(["free"])


def test_parse_deposit_command_negative_amount() -> None:
    with pytest.raises(InvalidAmountException):
        parse_deposit_command(["-100"])


def test_parse_deposit_command_zero_amount() -> None:
    with pytest.raises(InvalidAmountException):
        parse_deposit_command(["0"])
