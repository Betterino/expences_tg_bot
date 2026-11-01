# Shortcuts. Docker targets are for the server, the rest for local development.
PY := env/bin/python

.PHONY: up down restart logs ps test lint run

up:  ## build (runs the tests) and start in the background
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

test:
	$(PY) -m pytest -q

lint:
	env/bin/ruff check .

run:  ## run locally without Docker
	$(PY) -m expenses_bot
