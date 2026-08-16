import sqlite3
from datetime import UTC, datetime

import pytest

from trade_portfolio_bot.db.repository import PortfolioRepository
from trade_portfolio_bot.domain.cash import CashDeposit
from trade_portfolio_bot.domain.currency import Currency
from trade_portfolio_bot.domain.trade import Trade, TradeSide


def test_init_creates_schema(tmp_path):
    db_path = tmp_path / "test.db"
    PortfolioRepository(db_path)

    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"trades", "cash_deposits"} <= tables


def test_save_trade_persists_row(tmp_path):
    db_path = tmp_path / "test.db"
    repo = PortfolioRepository(db_path)
    trade = Trade(ticker="AAPL", side=TradeSide.BUY, quantity=10, price=150.5, timestamp=datetime.now(UTC))

    repo.save_trade(trade, user_id=111)
    repo.close()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT user_id, ticker, side, quantity, price FROM trades").fetchall()
    assert rows == [(111, "AAPL", "BUY", 10.0, 150.5)]


def test_save_deposit_persists_row(tmp_path):
    db_path = tmp_path / "test.db"
    repo = PortfolioRepository(db_path)
    cash = CashDeposit(amount=1000, timestamp=datetime.now(UTC))

    repo.save_deposit(cash, user_id=111)
    repo.close()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT user_id, amount FROM cash_deposits").fetchall()
    assert rows == [(111, 1000.0)]


def test_rows_are_attributable_to_the_correct_user(tmp_path):
    db_path = tmp_path / "test.db"
    repo = PortfolioRepository(db_path)
    trade_a = Trade(ticker="AAPL", side=TradeSide.BUY, quantity=10, price=150.5, timestamp=datetime.now(UTC))
    trade_b = Trade(ticker="MSFT", side=TradeSide.BUY, quantity=5, price=300.0, timestamp=datetime.now(UTC))

    repo.save_trade(trade_a, user_id=111)
    repo.save_trade(trade_b, user_id=222)
    repo.close()

    with sqlite3.connect(db_path) as conn:
        user_a_tickers = [row[0] for row in conn.execute("SELECT ticker FROM trades WHERE user_id = ?", (111,))]
        user_b_tickers = [row[0] for row in conn.execute("SELECT ticker FROM trades WHERE user_id = ?", (222,))]
    assert user_a_tickers == ["AAPL"]
    assert user_b_tickers == ["MSFT"]


def test_get_cash_balance_with_no_activity_is_zero(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    assert repo.get_cash_balance(user_id=111) == []


def test_get_cash_balance_ignores_trades(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=111)
    repo.save_trade(
        Trade(ticker="AAPL", side=TradeSide.BUY, quantity=10, price=150.5, timestamp=datetime.now(UTC)), user_id=111
    )
    repo.save_trade(
        Trade(ticker="AAPL", side=TradeSide.SELL, quantity=4, price=160.0, timestamp=datetime.now(UTC)), user_id=111
    )

    # Deposits only — buy/sell trades don't affect the cash figure.
    assert repo.get_cash_balance(user_id=111) == [("ILS", pytest.approx(1000.0))]


def test_get_cash_balance_sums_multiple_deposits(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=111)
    repo.save_deposit(CashDeposit(amount=250, timestamp=datetime.now(UTC)), user_id=111)

    assert repo.get_cash_balance(user_id=111) == [("ILS", pytest.approx(1250.0))]


def test_get_cash_balance_groups_by_currency(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=111, currency=Currency.ILS)
    repo.save_deposit(CashDeposit(amount=200, timestamp=datetime.now(UTC)), user_id=111, currency=Currency.USD)

    assert repo.get_cash_balance(user_id=111) == [
        ("ILS", pytest.approx(1000.0)),
        ("USD", pytest.approx(200.0)),
    ]


def test_get_cash_balance_is_scoped_per_user(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=111)
    repo.save_deposit(CashDeposit(amount=500, timestamp=datetime.now(UTC)), user_id=222)

    assert repo.get_cash_balance(user_id=111) == [("ILS", pytest.approx(1000.0))]
    assert repo.get_cash_balance(user_id=222) == [("ILS", pytest.approx(500.0))]


def _save_trade(repo, ticker, side, quantity, user_id):
    repo.save_trade(
        Trade(ticker=ticker, side=side, quantity=quantity, price=100.0, timestamp=datetime.now(UTC)), user_id=user_id
    )


def test_get_holdings_with_no_trades_is_empty(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    assert not repo.get_holdings(user_id=111)


def test_get_holdings_nets_buys_and_sells(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    _save_trade(repo, "AAPL", TradeSide.BUY, 10, user_id=111)
    _save_trade(repo, "AAPL", TradeSide.SELL, 4, user_id=111)

    assert repo.get_holdings(user_id=111) == [("AAPL", 6.0)]


def test_get_holdings_omits_fully_closed_positions(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    _save_trade(repo, "AAPL", TradeSide.BUY, 10, user_id=111)
    _save_trade(repo, "AAPL", TradeSide.SELL, 10, user_id=111)

    assert not repo.get_holdings(user_id=111)


def test_get_holdings_covers_multiple_tickers_sorted(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    _save_trade(repo, "MSFT", TradeSide.BUY, 3, user_id=111)
    _save_trade(repo, "AAPL", TradeSide.BUY, 5, user_id=111)

    assert repo.get_holdings(user_id=111) == [("AAPL", 5.0), ("MSFT", 3.0)]


def test_get_holdings_is_scoped_per_user(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    _save_trade(repo, "AAPL", TradeSide.BUY, 5, user_id=111)
    _save_trade(repo, "MSFT", TradeSide.BUY, 3, user_id=222)

    assert repo.get_holdings(user_id=111) == [("AAPL", 5.0)]
    assert repo.get_holdings(user_id=222) == [("MSFT", 3.0)]


def test_reset_user_data_clears_trades_and_deposits(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=111)
    _save_trade(repo, "AAPL", TradeSide.BUY, 10, user_id=111)

    repo.reset_user_data(user_id=111)

    assert repo.get_cash_balance(user_id=111) == []
    assert not repo.get_holdings(user_id=111)


def test_reset_user_data_leaves_other_users_untouched(tmp_path):
    repo = PortfolioRepository(tmp_path / "test.db")
    repo.save_deposit(CashDeposit(amount=1000, timestamp=datetime.now(UTC)), user_id=111)
    _save_trade(repo, "AAPL", TradeSide.BUY, 10, user_id=111)
    repo.save_deposit(CashDeposit(amount=500, timestamp=datetime.now(UTC)), user_id=222)
    _save_trade(repo, "MSFT", TradeSide.BUY, 3, user_id=222)

    repo.reset_user_data(user_id=111)

    assert repo.get_cash_balance(user_id=222) == [("ILS", pytest.approx(500.0))]
    assert repo.get_holdings(user_id=222) == [("MSFT", 3.0)]


def test_migrates_pre_currency_database_without_losing_data(tmp_path):
    """Simulates the real, already-deployed schema (no `currency` column) with actual rows in it,
    then opens it with PortfolioRepository and checks the migration backfills safely."""
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            );
            CREATE TABLE cash_deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                timestamp TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO trades (user_id, ticker, side, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (111, "APP", "BUY", 12.0, 10.0, "2026-08-15T16:22:51.029712+00:00"),
        )
        conn.execute(
            "INSERT INTO cash_deposits (user_id, amount, timestamp) VALUES (?, ?, ?)",
            (111, 100.0, "2026-08-15T15:56:17.754533+00:00"),
        )
        conn.commit()

    repo = PortfolioRepository(db_path)

    assert repo.get_holdings(user_id=111) == [("APP", 12.0)]
    assert repo.get_cash_balance(user_id=111) == [("ILS", pytest.approx(100.0))]

    with sqlite3.connect(db_path) as conn:
        trade_currency = conn.execute("SELECT currency FROM trades WHERE user_id = 111").fetchone()
        deposit_currency = conn.execute("SELECT currency FROM cash_deposits WHERE user_id = 111").fetchone()

    assert trade_currency == (None,)
    assert deposit_currency == ("ILS",)
