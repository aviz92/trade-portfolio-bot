import pytest

from trade_portfolio_bot.exceptions import (
    InvalidBuyCommandException,
    InvalidPriceException,
    InvalidQuantityException,
    InvalidTickerException,
)
from trade_portfolio_bot.trade import parse_buy_command


def test_parse_buy_command_valid():
    trade = parse_buy_command(["AAPL", "10", "150.5"])
    assert trade.ticker == "AAPL"
    assert trade.quantity == 10
    assert trade.price == 150.5
    assert trade.total_cost == pytest.approx(1505.0)


def test_parse_buy_command_lowercases_ticker_normalized_to_upper():
    trade = parse_buy_command(["aapl", "1", "100"])
    assert trade.ticker == "AAPL"


def test_parse_buy_command_wrong_arg_count():
    with pytest.raises(InvalidBuyCommandException):
        parse_buy_command(["AAPL", "10"])


def test_parse_buy_command_invalid_ticker():
    with pytest.raises(InvalidTickerException):
        parse_buy_command(["$$$", "10", "150.5"])


def test_parse_buy_command_non_numeric_quantity():
    with pytest.raises(InvalidQuantityException):
        parse_buy_command(["AAPL", "ten", "150.5"])


def test_parse_buy_command_negative_quantity():
    with pytest.raises(InvalidQuantityException):
        parse_buy_command(["AAPL", "-5", "150.5"])


def test_parse_buy_command_non_numeric_price():
    with pytest.raises(InvalidPriceException):
        parse_buy_command(["AAPL", "10", "free"])


def test_parse_buy_command_zero_price():
    with pytest.raises(InvalidPriceException):
        parse_buy_command(["AAPL", "10", "0"])
