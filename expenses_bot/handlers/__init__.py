from expenses_bot.sandbox.handlers import router as sandbox_router  # sandbox

from . import common, edit, expenses, fallback, history, importer, onboard, settings, stats

routers = (
    common.router,
    stats.router,
    importer.router,  # before expenses: F.document must win over waiting_amount
    expenses.router,
    onboard.router,
    settings.router,
    history.router,
    sandbox_router,  # sandbox
    edit.router,
    fallback.router,  # last: unconditional callback_query catch-all that would swallow later routers' events
)
