import sqlite3
from pathlib import Path

from trade_portfolio_bot.domain.cash import CashDeposit
from trade_portfolio_bot.domain.trade import Trade, TradeSide

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

    def get_cash_balance(self, user_id: int) -> float:
        """Total cash deposited by the user (ILS). Not netted against buy/sell trades — those are a
        separate, unlabeled currency, so mixing them into one number would be misleading."""
        (deposits,) = self._connection.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM cash_deposits WHERE user_id = ?", (user_id,)
        ).fetchone()
        return deposits

    def get_holdings(self, user_id: int) -> list[tuple[str, float]]:
        """Net quantity held per ticker (buys minus sells). Fully-closed positions are omitted."""
        rows = self._connection.execute(
            """
            SELECT ticker, SUM(CASE WHEN side = ? THEN quantity ELSE -quantity END) AS net_quantity
            FROM trades
            WHERE user_id = ?
            GROUP BY ticker
            HAVING net_quantity != 0
            ORDER BY ticker
            """,
            (TradeSide.BUY.value, user_id),
        ).fetchall()
        return list(rows)

    def close(self) -> None:
        self._connection.close()
