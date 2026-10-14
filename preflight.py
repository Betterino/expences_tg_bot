"""Pre-start gate: bot.py runs the test suite before polling and refuses to start on red.

The suite runs in a *subprocess*, never in the bot's own process:
- tests mount handlers.routers into their own Dispatcher, and a Router can only ever
  have one parent -- in-process, bot.py's include_router() would then raise;
- tests monkeypatch module globals and reconfigure the root logger, none of which
  should leak into the running bot;
- pytest's exit code is the whole contract: 0 means every test passed, anything else
  (failures, collection errors, "no tests collected") means don't start.
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
REPORT_DIR = Path("data/test_reports")
TIMEOUT_S = 300  # a hung test must not keep the bot down silently forever


class SuiteFailed(Exception):
    def __init__(self, report: Path, summary: str):
        super().__init__(summary)
        self.report = report
        self.summary = summary


def run_tests(report_dir: Path = REPORT_DIR, targets: tuple[str, ...] = ()) -> str:
    """Run pytest; return its summary line on success, raise SuiteFailed otherwise.

    `targets` narrows the run (tests/test_preflight.py uses it); empty means the
    whole suite, as configured by testpaths in pyproject.toml."""
    command = [sys.executable, "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider", *targets]
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=TIMEOUT_S)
        output, ok = result.stdout + result.stderr, result.returncode == 0
    except subprocess.TimeoutExpired as error:
        # TimeoutExpired always carries bytes, even with text=True.
        partial = b"".join(part or b"" for part in (error.stdout, error.stderr))
        output = partial.decode(errors="replace") + f"\n\nТесты не уложились в {TIMEOUT_S} с\n"
        ok = False

    lines = output.strip().splitlines()
    summary = lines[-1] if lines else "pytest ничего не вывел"
    if ok:
        return summary

    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"failed-{datetime.now():%Y-%m-%d_%H%M%S}.txt"
    report.write_text(f"$ {' '.join(command)}\n\n{output}", encoding="utf-8")
    raise SuiteFailed(report, summary)
