from aiogram.filters.callback_data import CallbackData


class SandboxCB(CallbackData, prefix="sbx"):
    """Screen state lives entirely in callback data -- no FSM anywhere in the sandbox.

    Every button is rebuilt on each render carrying the *next* state, which is the
    idiomatic aiogram pattern for a stateless screen: immune to the state.clear()
    calls scattered across the other handlers, and correct if the screen is open in
    two chats at once. Packs to ~22 of Telegram's 64 allowed bytes.
    """

    action: str  # show | copy
    key: str  # ключ варианта из sandbox.variants.VARIANTS
    source: str  # demo | empty | long | live
