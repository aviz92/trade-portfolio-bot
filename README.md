![Python](https://img.shields.io/badge/python->=3.12-blue)
![Development Status](https://img.shields.io/badge/status-alpha-orange)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
![License](https://img.shields.io/badge/license-MIT-green)

---

# 💡 trade-portfolio-bot
A Telegram bot for logging securities purchases and sales, and cash deposits, as you make them. Send `/buy TICKER QUANTITY PRICE`, `/sell TICKER QUANTITY PRICE`, or `/deposit AMOUNT` and the bot validates, logs, and confirms it back to you.

---

## 📦 Installation

```bash
git clone https://github.com/aviz92/trade-portfolio-bot.git
cd trade-portfolio-bot
uv sync --extra dev
```

---

## 🚀 Features
  - ✅ **`/buy TICKER QUANTITY PRICE`** — parses and validates a purchase, then logs and confirms it
  - ✅ **`/sell TICKER QUANTITY PRICE`** — parses and validates a sale, then logs and confirms it
  - ✅ **`/deposit AMOUNT`** — parses and validates cash added to your portfolio, then logs and confirms it
  - ✅ **Input validation** — rejects malformed tickers, non-numeric or non-positive quantity/price/amount with a clear reason
  - ✅ **Telegram command menu** — `/start`, `/help`, `/buy`, `/sell`, `/deposit` registered via `set_my_commands`
  - ✅ **Structured logging** — powered by `custom-python-logger`, with diagnostic context on rejected commands
  - ✅ **Typed custom exceptions** — `InvalidTickerException`, `InvalidQuantityException`, `InvalidPriceException`, `InvalidAmountException`, `InvalidTradeCommandException`, `InvalidCashCommandException` built on `python-custom-exceptions`

---

## ⚙️ Configuration

Create a `.env` file with the following variable:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
```

---

## 🛠️ How to Use
1. Step 1: Clone the repo and run `uv sync --extra dev`
2. Step 2: Create `.env` and set `TELEGRAM_BOT_TOKEN`
3. Step 3: Start the bot with `uv run bot`
4. Step 4: Message the bot on Telegram — `/start` for the welcome message, `/buy AAPL 10 150.5` to log a purchase, `/sell AAPL 5 160.0` to log a sale, `/deposit 1000` to log a cash deposit

---

## 🚀 Quick Start

```bash
uv sync --extra dev
echo "TELEGRAM_BOT_TOKEN=your_bot_token" > .env
uv run bot
```

---

## ▶️ Usage Examples
### Example 1: Parsing a buy or sell command
```python
from trade_portfolio_bot.domain.trade import TradeSide, parse_trade_command

trade = parse_trade_command(["aapl", "10", "150.5"], side=TradeSide.BUY)
print(trade.side, trade.ticker, trade.quantity, trade.price, trade.total_cost)
# TradeSide.BUY AAPL 10.0 150.5 1505.0

sale = parse_trade_command(["AAPL", "5", "160.0"], side=TradeSide.SELL)
print(sale.side, sale.ticker, sale.quantity, sale.price, sale.total_cost)
# TradeSide.SELL AAPL 5.0 160.0 800.0
```

### Example 2: Invalid input raises a typed exception
```python
from trade_portfolio_bot.domain.exceptions import InvalidQuantityException
from trade_portfolio_bot.domain.trade import TradeSide, parse_trade_command

try:
    parse_trade_command(["AAPL", "-5", "150.5"], side=TradeSide.BUY)
except InvalidQuantityException as e:
    print(e.message)
# Quantity must be greater than 0
```

### Example 3: Parsing a cash deposit
```python
from trade_portfolio_bot.domain.cash import parse_deposit_command

cash = parse_deposit_command(["1000"])
print(cash.amount)
# 1000.0
```

---

## 🗺️ Roadmap
- [ ] Persist trades (SQLite / Postgres via `python-databases`)
- [ ] `/portfolio` command to view holdings summary
- [ ] Export to CSV / Google Sheets

---

## 🤝 Contributing

If you have a helpful pattern or improvement to suggest:
Fork the repo
Create a new branch
Submit a pull request
I welcome additions that promote clean, productive, and maintainable development.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Thanks
Thanks for exploring this repository! <br>
Happy coding!

[![GitHub](https://img.shields.io/badge/GitHub-aviz92-181717?logo=github)](https://github.com/aviz92)
&nbsp; [![PyPI](https://img.shields.io/badge/PyPI-aviz-3775A9?logo=pypi)](https://pypi.org/user/aviz/)
&nbsp; [![Blog](https://img.shields.io/badge/Blog-aviz92.github.io-0066CC?logo=googlechrome)](https://aviz92.github.io/)
&nbsp; [![LinkedIn](https://img.shields.io/badge/LinkedIn-avi--zaguri-0A66C2?logo=linkedin)](https://www.linkedin.com/in/avi-zaguri-41869b11b)
