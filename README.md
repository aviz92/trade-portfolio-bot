# trade-portfolio-bot

A Telegram bot for logging securities purchases as you make them.

Send `/buy TICKER QUANTITY PRICE` and the bot logs the trade (currently to console) and confirms back to you.

## Usage

```
/buy AAPL 10 150.5
```

## Setup

```bash
uv sync --extra dev
cp .env.example .env
# edit .env and set TELEGRAM_BOT_TOKEN
uv run bot
```

## Roadmap

- [ ] Persist trades (SQLite / Postgres via `python-databases`)
- [ ] `/portfolio` command to view holdings summary
- [ ] Support `/sell`
- [ ] Export to CSV / Google Sheets
