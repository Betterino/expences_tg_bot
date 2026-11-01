# Three stages. `base` installs the runtime deps once; `test` and `runtime` both start
# from it, so that layer is built (and cached) a single time.
#
#   docker compose build   ->  base -> test (ruff + pytest) -> runtime
#
# A red suite fails the `test` stage, and `runtime` depends on a file that only a green
# `test` stage produces -- so a broken version can never become an image.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
# Requirements first, code later: this layer is only rebuilt when requirements.txt
# changes, not on every code edit.
COPY requirements.txt .
RUN pip install -r requirements.txt


FROM base AS test
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY pyproject.toml CHANGELOG.md ./
COPY expenses_bot/ expenses_bot/
COPY tests/ tests/
RUN ruff check . && python -m pytest -q -p no:cacheprovider && touch /tests-passed


FROM base AS runtime
# Matches the host user that owns ./data, so the bind-mounted directory is writable.
ARG UID=1000
ARG GID=1000
RUN groupadd --gid "$GID" bot && useradd --uid "$UID" --gid "$GID" --no-create-home bot
# BuildKit only builds stages the target needs: without this line it would skip `test`.
COPY --from=test /tests-passed /tmp/tests-passed
COPY expenses_bot/ expenses_bot/
ENV DATA_DIR=/app/data
RUN mkdir -p "$DATA_DIR" && chown bot:bot "$DATA_DIR"
USER bot
CMD ["python", "-m", "expenses_bot"]
