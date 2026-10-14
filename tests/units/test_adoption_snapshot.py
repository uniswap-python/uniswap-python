"""Unit tests for scripts/adoption_snapshot.py traffic reconstruction.

No network. The grant D4 report must not subtract two rolling 14-day windows.
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "adoption_snapshot.py"


def _mod() -> Any:
    spec = importlib.util.spec_from_file_location("adoption_snapshot", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _daily(start: str, counts: List[int]) -> List[Dict[str, Any]]:
    d = date.fromisoformat(start)
    rows = []
    for n in counts:
        rows.append({"date": d.isoformat(), "count": n, "uniques": 1})
        d += timedelta(days=1)
    return rows


def _snap(day: str, clones: List[Dict[str, Any]], clones_14d: int) -> Dict[str, Any]:
    return {
        "snapshot_at": day + "T06:00:00+00:00",
        "github": {"stars": 1000},
        "github_traffic": {
            "clones_14d": clones_14d,
            "unique_cloners_14d": 10,
            "views_14d": clones_14d,
            "unique_visitors_14d": 10,
            "clones_daily": clones,
            "views_daily": clones,
        },
        "pypi": {},
    }


def test_reconstruct_unions_days_without_double_counting() -> None:
    snap = _mod()
    # Two adjacent 14-day windows. Naive subtraction of 14d totals is 80-100=-20.
    a = _snap("2026-09-02", _daily("2026-08-20", [10] * 14), clones_14d=140)
    b = _snap("2026-09-16", _daily("2026-09-03", [5] * 14), clones_14d=70)
    # Period 09-02 → 09-16 = 09-02 (10) + 14 days of 5 = 80
    result = snap.reconstruct_period_counts(
        [a, b], "2026-09-02", "2026-09-16", "clones_daily"
    )
    assert result["total"] == 10 + 5 * 14
    assert result["days_covered"] == 15
    assert result["days_span"] == 15
    assert result["missing_days"] == []
    naive = 70 - 140
    assert result["total"] != naive
    assert result["total"] > 0


def test_reconstruct_takes_max_on_overlapping_same_day() -> None:
    snap = _mod()
    early = _snap(
        "2026-09-02",
        [{"date": "2026-09-02", "count": 3, "uniques": 1}],
        clones_14d=3,
    )
    later = _snap(
        "2026-09-02",
        [{"date": "2026-09-02", "count": 8, "uniques": 2}],
        clones_14d=8,
    )
    result = snap.reconstruct_period_counts(
        [early, later], "2026-09-02", "2026-09-02", "clones_daily"
    )
    assert result["total"] == 8


def test_reconstruct_lists_gaps() -> None:
    snap = _mod()
    a = _snap(
        "2026-09-02",
        [{"date": "2026-09-02", "count": 1, "uniques": 1}],
        clones_14d=1,
    )
    b = _snap(
        "2026-09-05",
        [{"date": "2026-09-05", "count": 1, "uniques": 1}],
        clones_14d=1,
    )
    result = snap.reconstruct_period_counts(
        [a, b], "2026-09-02", "2026-09-05", "clones_daily"
    )
    assert result["total"] == 2
    assert result["missing_days"] == ["2026-09-03", "2026-09-04"]


def test_format_report_does_not_subtract_rolling_windows() -> None:
    snap = _mod()
    baseline = _snap("2026-09-02", _daily("2026-08-20", [10] * 14), clones_14d=140)
    current = _snap("2026-09-16", _daily("2026-09-03", [5] * 14), clones_14d=70)
    # Freeze now to the day *after* current so 2026-09-16 is a complete day.
    report = snap.format_report(
        baseline, current, snapshots=[baseline, current], now=date(2026, 9, 17)
    )
    assert "-20" not in report
    assert "-70" not in report
    # Naive 14d delta would be 70-140. Reconstructed period clones = 80.
    assert "| Clones | 80 |" in report
    assert "not subtracted" in report
    assert "Period totals (2026-09-02 → 2026-09-16)" in report
    # 14d table has no Delta column
    assert "Rolling 14-day windows (point-in-time, not a period delta)" in report
    traffic_header = "### Rolling 14-day windows"
    idx = report.index(traffic_header)
    rolling = report[idx : idx + 600]
    assert "Delta" not in rolling


def test_complete_period_end_drops_today() -> None:
    snap = _mod()
    closed, excluded = snap.complete_period_end("2026-09-16", now=date(2026, 9, 16))
    assert closed == "2026-09-15"
    assert excluded == "2026-09-16"
    closed, excluded = snap.complete_period_end("2026-09-16", now=date(2026, 9, 17))
    assert closed == "2026-09-16"
    assert excluded is None


def test_complete_period_end_without_now_uses_snapshot_day() -> None:
    """Production default must not re-read datetime.now().

    If collection starts on 09-16 and midnight passes during network I/O,
    a fresh clock would skip exclusion and publish 09-16's partial row.
    """
    snap = _mod()
    closed, excluded = snap.complete_period_end("2026-09-16")
    assert closed == "2026-09-15"
    assert excluded == "2026-09-16"
    closed, excluded = snap.complete_period_end("not-a-date")
    assert closed == "not-a-date"
    assert excluded is None


def test_format_report_excludes_partial_current_utc_day() -> None:
    snap = _mod()
    baseline = _snap("2026-09-02", _daily("2026-08-20", [10] * 14), clones_14d=140)
    current = _snap("2026-09-16", _daily("2026-09-03", [5] * 14), clones_14d=70)
    report = snap.format_report(
        baseline, current, snapshots=[baseline, current], now=date(2026, 9, 16)
    )
    # 09-02 (10) + 09-03..09-15 (13*5) = 75; 09-16's partial 5 is dropped.
    assert "| Clones | 75 |" in report
    assert "Period totals (2026-09-02 → 2026-09-15)" in report
    assert "2026-09-16 excluded" in report
    assert "| Clones | 80 |" not in report


def test_format_report_midnight_crossing_excludes_collection_day() -> None:
    """Wall clock after midnight must not resurrect the partial collection day.

    collect_metrics stamps snapshot_at first, then does network I/O.
    format_report() with now=None (the production default) must key off
    snapshot_at, not datetime.now().
    """
    snap = _mod()
    baseline = _snap("2026-09-02", _daily("2026-08-20", [10] * 14), clones_14d=140)
    current = _snap("2026-09-16", _daily("2026-09-03", [5] * 14), clones_14d=70)
    report = snap.format_report(baseline, current, snapshots=[baseline, current])
    assert "| Clones | 75 |" in report
    assert "Period totals (2026-09-02 → 2026-09-15)" in report
    assert "2026-09-16 excluded" in report
    assert "| Clones | 80 |" not in report


def test_format_report_baseline_today_has_no_complete_days() -> None:
    snap = _mod()
    baseline = _snap(
        "2026-09-02",
        [{"date": "2026-09-02", "count": 3, "uniques": 1}],
        clones_14d=3,
    )
    report = snap.format_report(
        baseline, baseline, snapshots=[baseline], now=date(2026, 9, 2)
    )
    assert "No complete UTC days" in report
    assert "Period totals (" not in report


def test_format_report_without_daily_series_does_not_invent_delta() -> None:
    snap = _mod()
    baseline = {
        "snapshot_at": "2026-09-02T00:00:00+00:00",
        "github": {"stars": 1000, "forks": 1, "watchers": 1},
        "github_traffic": {"clones_14d": 100, "views_14d": 200},
        "pypi": {},
    }
    current = {
        "snapshot_at": "2026-11-01T00:00:00+00:00",
        "github": {"stars": 1100, "forks": 2, "watchers": 1},
        "github_traffic": {"clones_14d": 40, "views_14d": 50},
        "pypi": {},
    }
    report = snap.format_report(baseline, current, now=date(2026, 11, 2))
    assert "Period totals unavailable" in report
    assert "-60" not in report  # 40-100
    assert "-150" not in report  # 50-200
    # Stars *are* cumulative; that delta is honest.
    assert "+100" in report


def test_traffic_daily_series_normalizes_github_payload() -> None:
    snap = _mod()
    payload = {
        "count": 5,
        "uniques": 3,
        "clones": [
            {"timestamp": "2026-09-01T00:00:00Z", "count": 2, "uniques": 1},
            {"timestamp": "2026-09-02T00:00:00Z", "count": 3, "uniques": 2},
        ],
    }
    rows = snap._traffic_daily_series(payload, "clones")
    assert rows == [
        {"date": "2026-09-01", "count": 2, "uniques": 1},
        {"date": "2026-09-02", "count": 3, "uniques": 2},
    ]
