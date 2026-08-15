from dataclasses import dataclass
from datetime import datetime, timezone

from trade_portfolio_bot.exceptions import (
    InvalidBuyCommandException,
    InvalidPriceException,
    InvalidQuantityException,
    InvalidTickerException,
)


@dataclass(frozen=True)
class Trade:
    ticker: str
    quantity: float
    price: float
    timestamp: datetime

    @property
    def total_cost(self) -> float:
        return self.quantity * self.price

    def __str__(self) -> str:
        return (
            f"{self.ticker} | qty={self.quantity} | price={self.price} "
            f"| total={self.total_cost:.2f} | {self.timestamp.isoformat()}"
        )


def parse_buy_command(args: list[str]) -> Trade:
    """
    Parse /buy command arguments into a Trade.

    Expected format: /buy TICKER QUANTITY PRICE
    Example: /buy AAPL 10 150.5
    """
    if len(args) != 3:
        raise InvalidBuyCommandException(
            "Expected 3 arguments: TICKER QUANTITY PRICE",
            diagnostic_info={"args": args},
        )

    raw_ticker, raw_quantity, raw_price = args

    ticker = raw_ticker.strip().upper()
    if not ticker.isalnum() or len(ticker) > 10:
        raise InvalidTickerException(
            f"'{raw_ticker}' does not look like a valid ticker symbol",
            diagnostic_info={"ticker": raw_ticker},
        )

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

    return Trade(ticker=ticker, quantity=quantity, price=price, timestamp=datetime.now(timezone.utc))
