from . import common, expenses, stats, edit, onboard, settings

routers = (
    common.router,
    stats.router,
    expenses.router,
    onboard.router,
    settings.router,
    edit.router
    
)