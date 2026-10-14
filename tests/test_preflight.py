"""The pre-start gate (preflight.py) against throwaway one-test files.

Every call passes explicit `targets`: run_tests() with no targets runs the *whole*
suite -- including this file, which would call it again, forever."""
import pytest

from preflight import SuiteFailed, run_tests


def _write_test(tmp_path, body: str) -> str:
    path = tmp_path / "test_probe.py"
    path.write_text(f"def test_probe():\n    {body}\n", encoding="utf-8")
    return str(path)


def test_green_run_returns_summary_and_writes_no_report(tmp_path) -> None:
    report_dir = tmp_path / "reports"
    summary = run_tests(report_dir, targets=(_write_test(tmp_path, "assert True"),))
    assert "1 passed" in summary
    assert not report_dir.exists()


def test_red_run_writes_report_and_raises(tmp_path) -> None:
    report_dir = tmp_path / "reports"
    with pytest.raises(SuiteFailed) as failure:
        run_tests(report_dir, targets=(_write_test(tmp_path, "assert 1 == 2"),))
    assert "1 failed" in failure.value.summary
    assert failure.value.report.parent == report_dir
    report = failure.value.report.read_text(encoding="utf-8")
    assert "test_probe" in report and "assert 1 == 2" in report


def test_collection_error_counts_as_red(tmp_path) -> None:
    """A test file that doesn't even import must block the start too, not slip through
    as "0 failed"."""
    broken = tmp_path / "test_broken.py"
    broken.write_text("import module_that_does_not_exist\n", encoding="utf-8")
    with pytest.raises(SuiteFailed) as failure:
        run_tests(tmp_path / "reports", targets=(str(broken),))
    assert "module_that_does_not_exist" in failure.value.report.read_text(encoding="utf-8")
