from aiogram.types import Update

MAX_TEXT_LEN = 100


def describe_update(update: Update) -> str:
    """One-line human-readable summary of an incoming update, for logging."""
    user = None
    if update.message is not None:
        user = update.message.from_user
    elif update.callback_query is not None:
        user = update.callback_query.from_user
    user_part = f"user={user.id} @{user.username}" if user else "user=?"

    if update.message is not None:
        chat_id = update.message.chat.id
        text = (update.message.text or "")[:MAX_TEXT_LEN]
        return f"upd={update.update_id} msg  {user_part} chat={chat_id} text={text!r}"
    if update.callback_query is not None:
        chat_id = update.callback_query.message.chat.id if update.callback_query.message else "?"
        return f"upd={update.update_id} cb   {user_part} chat={chat_id} data={update.callback_query.data!r}"
    return f"upd={update.update_id} {update.event_type} {user_part}"
