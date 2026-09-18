from . import common, expenses, stats, edit, onboard, settings, history
from sandbox.handlers import router as sandbox_router  # sandbox

routers = (
    common.router,
    stats.router,
    expenses.router,
    onboard.router,
    settings.router,
    history.router,
    sandbox_router,  # sandbox
    edit.router,  # last: has an unconditional callback_query catch-all that would swallow later routers' events
)