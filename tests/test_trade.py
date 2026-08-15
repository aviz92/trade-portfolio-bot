import pytest

from trade_portfolio_bot.domain.exceptions import (
    InvalidPriceException,
    InvalidQuantityException,
    InvalidTickerException,
    InvalidTradeCommandException,
)
from trade_portfolio_bot.domain.trade import TradeSide, parse_trade_command


def test_parse_trade_command_valid_buy():
    trade = parse_trade_command(["AAPL", "10", "150.5"], side=TradeSide.BUY)
    assert trade.side == TradeSide.BUY
    assert trade.ticker == "AAPL"
    assert trade.quantity == 10
    assert trade.price == 150.5
    assert trade.total_cost == pytest.approx(1505.0)


def test_parse_trade_command_valid_sell():
    trade = parse_trade_command(["AAPL", "5", "160.0"], side=TradeSide.SELL)
    assert trade.side == TradeSide.SELL
    assert trade.ticker == "AAPL"
    assert trade.quantity == 5
    assert trade.price == 160.0


def test_parse_trade_command_lowercases_ticker_normalized_to_upper():
    trade = parse_trade_command(["aapl", "1", "100"], side=TradeSide.BUY)
    assert trade.ticker == "AAPL"


def test_parse_trade_command_wrong_arg_count():
    with pytest.raises(InvalidTradeCommandException):
        parse_trade_command(["AAPL", "10"], side=TradeSide.BUY)


def test_parse_trade_command_invalid_ticker():
    with pytest.raises(InvalidTickerException):
        parse_trade_command(["$$$", "10", "150.5"], side=TradeSide.BUY)


def test_parse_trade_command_non_numeric_quantity():
    with pytest.raises(InvalidQuantityException):
        parse_trade_command(["AAPL", "ten", "150.5"], side=TradeSide.BUY)


def test_parse_trade_command_negative_quantity():
    with pytest.raises(InvalidQuantityException):
        parse_trade_command(["AAPL", "-5", "150.5"], side=TradeSide.BUY)


def test_parse_trade_command_non_numeric_price():
    with pytest.raises(InvalidPriceException):
        parse_trade_command(["AAPL", "10", "free"], side=TradeSide.BUY)


def test_parse_trade_command_zero_price():
    with pytest.raises(InvalidPriceException):
        parse_trade_command(["AAPL", "10", "0"], side=TradeSide.BUY)
