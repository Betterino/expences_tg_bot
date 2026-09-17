from . import common, expenses, stats, edit, onboard, settings, history

routers = (
    common.router,
    stats.router,
    expenses.router,
    onboard.router,
    settings.router,
    history.router,
    edit.router,  # last: has an unconditional callback_query catch-all that would swallow later routers' events
)