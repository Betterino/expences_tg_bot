from . import common, expenses, stats, edit, onboard, settings, history

routers = (
    common.router,
    stats.router,
    expenses.router,
    onboard.router,
    settings.router,
    edit.router,
    history.router,
)