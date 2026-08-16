import sqlite3
from pathlib import Path

from trade_portfolio_bot.domain.cash import CashDeposit
from trade_portfolio_bot.domain.currency import Currency
from trade_portfolio_bot.domain.trade import Trade, TradeSide

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    currency TEXT,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trades_user_id ON trades(user_id);

CREATE TABLE IF NOT EXISTS cash_deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'ILS',
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
        self._ensure_currency_columns()

    def _ensure_currency_columns(self) -> None:
        """Backfills the `currency` column onto databases created before it existed.

        `trades` is left nullable (NULL = currency was never chosen, e.g. pre-existing rows) since
        nothing computes on it. `cash_deposits` backfills to 'ILS', matching this bot's prior
        deposit-is-always-ILS behavior.
        """
        trades_columns = {row[1] for row in self._connection.execute("PRAGMA table_info(trades)")}
        if "currency" not in trades_columns:
            self._connection.execute("ALTER TABLE trades ADD COLUMN currency TEXT")

        deposit_columns = {row[1] for row in self._connection.execute("PRAGMA table_info(cash_deposits)")}
        if "currency" not in deposit_columns:
            self._connection.execute("ALTER TABLE cash_deposits ADD COLUMN currency TEXT NOT NULL DEFAULT 'ILS'")

        self._connection.commit()

    def save_trade(self, trade: Trade, user_id: int, currency: Currency | None = None) -> None:
        self._connection.execute(
            "INSERT INTO trades (user_id, ticker, side, quantity, price, currency, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                trade.ticker,
                trade.side.value,
                trade.quantity,
                trade.price,
                currency.value if currency else None,
                trade.timestamp.isoformat(),
            ),
        )
        self._connection.commit()

    def save_deposit(self, cash: CashDeposit, user_id: int, currency: Currency = Currency.ILS) -> None:
        self._connection.execute(
            "INSERT INTO cash_deposits (user_id, amount, currency, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, cash.amount, currency.value, cash.timestamp.isoformat()),
        )
        self._connection.commit()

    def get_cash_balance(self, user_id: int) -> list[tuple[str, float]]:
        """Total cash deposited by the user, grouped by currency (deposits can be ILS or USD).
        Not netted against buy/sell trades — those track a separate currency per trade."""
        rows = self._connection.execute(
            "SELECT currency, COALESCE(SUM(amount), 0) FROM cash_deposits WHERE user_id = ? "
            "GROUP BY currency ORDER BY currency",
            (user_id,),
        ).fetchall()
        return list(rows)

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

    def reset_user_data(self, user_id: int) -> None:
        """Deletes all trades and cash deposits for a user. Other users' data is untouched."""
        self._connection.execute("DELETE FROM trades WHERE user_id = ?", (user_id,))
        self._connection.execute("DELETE FROM cash_deposits WHERE user_id = ?", (user_id,))
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()
