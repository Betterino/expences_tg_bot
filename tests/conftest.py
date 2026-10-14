"""Shared pytest fixtures. pytest discovers this file by name and injects a fixture into
any test whose parameter has the same name -- no import needed in the test modules."""
import pytest
from aiogram import Dispatcher

from db import Database
from handlers import routers


@pytest.fixture
async def db(tmp_path) -> Database:
    """A fresh, fully migrated database per test. `tmp_path` is pytest's own per-test
    temporary directory; the `async with` closes the connection after the test, even
    if it failed."""
    async with Database(tmp_path / "test.db") as database:
        yield database


@pytest.fixture(scope="session")
def dispatcher() -> Dispatcher:
    """handlers.routers mounted once, in the order bot.py mounts them.

    Router.parent_router is a one-time assignment -- aiogram refuses to attach the same
    Router to a second Dispatcher in one process. Session scope builds the chain once
    and hands the same object to every full-stack routing test."""
    dp = Dispatcher()
    for router in routers:
        dp.include_router(router)
    return dp
