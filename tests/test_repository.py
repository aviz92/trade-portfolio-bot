import sqlite3
from datetime import UTC, datetime

from trade_portfolio_bot.db.repository import PortfolioRepository
from trade_portfolio_bot.domain.cash import CashDeposit
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
