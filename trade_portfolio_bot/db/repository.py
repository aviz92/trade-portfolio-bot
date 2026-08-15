import sqlite3
from pathlib import Path

from trade_portfolio_bot.domain.cash import CashDeposit
from trade_portfolio_bot.domain.trade import Trade

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);

CREATE TABLE IF NOT EXISTS cash_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cash_deposits_user_id ON cash_deposits(user_id);
"""


class PortfolioRepository:
    """Persists trades and cash deposits to a local SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self._connection = sqlite3.connect(db_path)
        self._connection.executescript(_SCHEMA)
        self._connection.commit()

    def save_trade(self, trade: Trade, user_id: int) -> None:
        self._connection.execute(
            "INSERT INTO trades (user_id, ticker, side, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, trade.ticker, trade.side.value, trade.quantity, trade.price, trade.timestamp.isoformat()),
        )
        self._connection.commit()

    def save_deposit(self, cash: CashDeposit, user_id: int) -> None:
        self._connection.execute(
            "INSERT INTO cash_deposits (user_id, amount, timestamp) VALUES (?, ?, ?)",
            (user_id, cash.amount, cash.timestamp.isoformat()),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()
