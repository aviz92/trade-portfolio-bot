from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from trade_portfolio_bot.domain.exceptions import (
    InvalidPriceException,
    InvalidQuantityException,
    InvalidTickerException,
    InvalidTradeCommandException,
)


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Trade:
    ticker: str
    side: TradeSide
    quantity: float
    price: float
    timestamp: datetime

    @property
    def total_cost(self) -> float:
        return self.quantity * self.price

    def __str__(self) -> str:
        return (
            f"{self.side.value} {self.ticker} | qty={self.quantity} | price={self.price} "
            f"| total={self.total_cost:.2f} | {self.timestamp.isoformat()}"
        )


def _parse_ticker(raw_ticker: str) -> str:
    ticker = raw_ticker.strip().upper()
    if not ticker.isalnum() or len(ticker) > 10:
        raise InvalidTickerException(
            f"'{raw_ticker}' does not look like a valid ticker symbol",
            diagnostic_info={"ticker": raw_ticker},
        )
    return ticker


def _parse_quantity(raw_quantity: str) -> float:
    try:
        quantity = float(raw_quantity)
    except ValueError as e:
        raise InvalidQuantityException(
            f"'{raw_quantity}' is not a valid number",
            diagnostic_info={"quantity": raw_quantity},
        ) from e
    if quantity <= 0:
        raise InvalidQuantityException(
            "Quantity must be greater than 0",
            diagnostic_info={"quantity": quantity},
        )
    return quantity


def _parse_price(raw_price: str) -> float:
    try:
        price = float(raw_price)
    except ValueError as e:
        raise InvalidPriceException(
            f"'{raw_price}' is not a valid number",
            diagnostic_info={"price": raw_price},
        ) from e
    if price <= 0:
        raise InvalidPriceException(
            "Price must be greater than 0",
            diagnostic_info={"price": price},
        )
    return price


def parse_trade_command(args: list[str], side: TradeSide) -> Trade:
    """
    Parse /buy or /sell command arguments into a Trade.

    Expected format: TICKER QUANTITY PRICE
    Example: AAPL 10 150.5
    """
    if len(args) != 3:
        raise InvalidTradeCommandException(
            "Expected 3 arguments: TICKER QUANTITY PRICE",
            diagnostic_info={"args": args},
        )

    raw_ticker, raw_quantity, raw_price = args
    ticker = _parse_ticker(raw_ticker)
    quantity = _parse_quantity(raw_quantity)
    price = _parse_price(raw_price)

    return Trade(ticker=ticker, side=side, quantity=quantity, price=price, timestamp=datetime.now(UTC))
