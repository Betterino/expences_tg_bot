# expences_tg_bot

Telegram bot for tracking shared expenses and income (aiogram 3, SQLite).

## Layout

```
expenses_bot/        the bot (python -m expenses_bot)
  app.py             Dispatcher, middlewares, error handler, main()
  config.py          everything read from the environment
  constants.py       VERSION and other static values
  db.py              SQLite access, migrations, daily backups
  ui/                callback data, keyboards, texts, views, richtext blocks
  handlers/          one router per feature, fallback mounted last
  sandbox/           admin-only playground for table styles
tests/               pytest suite (run at image build)
data/                runtime only, gitignored: expenses.db, backups/, logs/
```

## Configuration

Copy `.env.example` to `.env` and fill in `API_KEY` (and `ADMIN_ID` to see the
🧪 sandbox). Values are read from environment variables; `.env` is loaded for local
runs and passed in via `env_file` under Docker — it is never copied into the image.

## Run on a server (Docker)

```
make up       # docker compose up -d --build — builds, runs ruff + tests, starts
make logs     # follow output
make down     # stop
```

The image build runs the full test suite: if anything is red, no image is built and
the running container is left untouched. The bot restarts on crash and after reboot
(`restart: unless-stopped`). `./data` is bind-mounted, so the database survives
rebuilds. The container runs as uid/gid 1000; if the host user differs, build with
`UID=$(id -u) GID=$(id -g) docker compose up -d --build`.

## Run locally

```
python -m venv env && env/bin/pip install -r requirements-dev.txt
make run      # env/bin/python -m expenses_bot
make test     # pytest
make lint     # ruff
```

## Moving to a new server

1. Old server: stop the bot, copy `data/` (expenses.db + backups/) and `.env`.
2. New server: `git clone`, put `.env` and `data/` into the repo root, `make up`.
3. `make logs` until polling starts, then open the bot and tap «Меню».

Only one instance may poll a token at a time — stop the old one first.

## Restoring from a backup

`make down`, copy a file from `data/backups/` over `data/expenses.db`, `make up`.
