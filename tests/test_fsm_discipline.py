"""Keeps postmortems/2026-10-05-add-expense-mode-keyerror.md from coming back.

FSM data written by one update can be gone (state.clear() on every "Меню" tap) by the
time a later update reads it, so a bare data["key"] on `await state.get_data()` is a
KeyError waiting for a stale button. Handlers read through handlers/flow.require_flow
(which returns the same dict, but only once the keys are known to be there) or use
.get() and handle the None themselves (stats.input_month's "from_month").

Checked statically with ast, per function: a name bound from `await <x>.get_data()`
must never be subscripted. Names bound from require_flow(...) are not tracked -- that
is the point of it.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKED_DIRS = ("handlers", "sandbox")


def _is_raw_get_data(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "get_data"
    )


def _violations(source: str, filename: str) -> list[str]:
    found = []
    tree = ast.parse(source, filename=filename)
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        raw_names = {
            target.id
            for node in ast.walk(func)
            if isinstance(node, ast.Assign) and _is_raw_get_data(node.value)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in raw_names
                and isinstance(node.ctx, ast.Load)
            ):
                found.append(f"{filename}:{node.lineno} {node.value.id}[...] on raw get_data()")
    return found


def test_checker_catches_a_raw_subscript() -> None:
    """The check itself, against a snippet that has the bug -- an AST walk that silently
    matches nothing would otherwise pass forever."""
    bad = "async def h(state):\n    data = await state.get_data()\n    return data['mode']\n"
    good = "async def h(state):\n    data = await state.get_data()\n    return data.get('mode')\n"
    assert _violations(bad, "bad.py") == ["bad.py:3 data[...] on raw get_data()"]
    assert _violations(good, "good.py") == []


def test_no_handler_subscripts_raw_fsm_data() -> None:
    found = []
    for directory in CHECKED_DIRS:
        for path in sorted((REPO_ROOT / directory).glob("*.py")):
            found += _violations(path.read_text(encoding="utf-8"), str(path.relative_to(REPO_ROOT)))
    assert not found, "use require_flow() or .get():\n" + "\n".join(found)
