#!/usr/bin/env python3
"""
adoption_snapshot.py — Uniswap-Python Adoption Metrics

Usage:
  python3 scripts/adoption_snapshot.py [--out DIR]
  python3 scripts/adoption_snapshot.py --report BASELINE.json

Modes:
  Snapshot (default): Emits a dated JSON + Markdown snapshot of:
    - GitHub stars, forks, watchers, open issues
    - GitHub Traffic: clones + unique visitors (14-day window — run frequently!)
    - PyPI downloads last day/week/month (pypistats.org API)
    - Recent release versions and dates

  Report (--report BASELINE.json): reads current metrics + a saved baseline
    and prints a D4 table. Stars/forks/watchers are true cumulative counters
    (delta is current − baseline). GitHub traffic is a rolling 14-day window —
    those totals are NEVER subtracted. Period clone/view counts are
    reconstructed by unioning the daily series stored in each snapshot.
    The current UTC day is excluded from period totals — its Traffic row is
    still accumulating (the 06:00 UTC scheduled run would otherwise undercount).

GitHub Traffic cannot be read with GitHub Actions' default GITHUB_TOKEN
(it 403s even with contents: write). Use a PAT:

  Fine-grained: Repository permissions → Administration: Read, Contents: Read
  Classic: public_repo (or repo)

  ADOPTION_GITHUB_TOKEN=github_pat_... python3 scripts/adoption_snapshot.py
  # GITHUB_TOKEN is also accepted for local/manual runs

Without a PAT, traffic metrics are omitted (other metrics still work).
The daily workflow reads repo secret ADOPTION_GITHUB_TOKEN and runs --strict
so a failed collector does not get committed as a successful snapshot.

Version-split download counts require BigQuery — not yet wired; see TODO below.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = "uniswap-python/uniswap-python"
PACKAGE = "uniswap-python"
USER_AGENT = f"{PACKAGE}-adoption-tracker/1.0; +https://github.com/{REPO}"

# Actions GITHUB_TOKEN always 403s on /traffic/* — needs a PAT instead.
_ACTIONS_TOKEN_PREFIXES = ("ghs_",)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request_json(
    url: str,
    headers: dict | None = None,
    retries: int = 5,
) -> tuple[dict | list | None, str | None]:
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    last_err: str | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read()), None
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.reason}"
            retryable = e.code in (429, 500, 502, 503, 504) and attempt < retries - 1
            if retryable:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                try:
                    delay = min(int(retry_after), 30) if retry_after else 2 ** (attempt + 1)
                except (TypeError, ValueError):
                    delay = 2 ** (attempt + 1)
                # pypistats.org 429s with no Retry-After; give it a couple of seconds.
                time.sleep(max(delay, 2))
                continue
            return None, last_err
        except Exception as e:
            return None, str(e)
    return None, last_err


def _gh(path: str, token: str | None = None) -> tuple[dict | list | None, str | None]:
    base = f"https://api.github.com/repos/{REPO}"
    url = f"{base}/{path}" if path else base
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _request_json(url, headers)


def _fetch_json(url: str, headers: dict | None = None) -> tuple[dict | None, str | None]:
    data, err = _request_json(url, headers)
    if isinstance(data, list):
        return None, "expected JSON object, got list"
    return data, err


def _is_actions_token(token: str) -> bool:
    return token.startswith(_ACTIONS_TOKEN_PREFIXES)


def _traffic_daily_series(payload: dict | None, series_key: str) -> list[dict]:
    """Normalize GitHub Traffic ``clones``/``views`` arrays to ``[{date, count, uniques}]``."""
    if not isinstance(payload, dict):
        return []
    rows: list[dict] = []
    for item in payload.get(series_key) or []:
        if not isinstance(item, dict):
            continue
        day = str(item.get("timestamp") or "")[:10]
        if len(day) != 10:
            continue
        rows.append(
            {
                "date": day,
                "count": item.get("count"),
                "uniques": item.get("uniques"),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------


def _collect_github(token: str | None) -> dict:
    data, err = _gh("", token)
    if err:
        return {"error": err}
    return {
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "watchers": data.get("subscribers_count"),
        "open_issues": data.get("open_issues_count"),
    }


def _collect_traffic(token: str | None) -> dict:
    if not token:
        return {
            "note": (
                "Skipped — set ADOPTION_GITHUB_TOKEN (PAT with Administration:read) "
                "to capture traffic (14-day window only). The default Actions "
                "GITHUB_TOKEN cannot read /traffic/*."
            )
        }
    if _is_actions_token(token):
        return {
            "error": (
                "GitHub Actions GITHUB_TOKEN cannot access the Traffic API "
                "(403 even with contents: write). Set repo secret "
                "ADOPTION_GITHUB_TOKEN to a PAT with Administration:read "
                "(fine-grained) or public_repo (classic)."
            )
        }

    # per=day keeps a reconstructable series. per=week would drop daily
    # resolution and make period totals over >14 days impossible.
    clones, c_err = _gh("traffic/clones?per=day", token)
    views, v_err = _gh("traffic/views?per=day", token)
    clones_d = clones if isinstance(clones, dict) else None
    views_d = views if isinstance(views, dict) else None
    result: dict = {
        "clones_14d": clones_d.get("count") if clones_d else None,
        "unique_cloners_14d": clones_d.get("uniques") if clones_d else None,
        "views_14d": views_d.get("count") if views_d else None,
        "unique_visitors_14d": views_d.get("uniques") if views_d else None,
        "clones_daily": _traffic_daily_series(clones_d, "clones"),
        "views_daily": _traffic_daily_series(views_d, "views"),
    }
    if c_err:
        result["clones_error"] = c_err
    if v_err:
        result["views_error"] = v_err
    return result


def _collect_pypi_recent() -> dict:
    # TODO: version-split downloads require BigQuery or a scraper not yet wired.
    # pypistats.org /recent gives overall day/week/month totals only.
    url = f"https://pypistats.org/api/packages/{PACKAGE}/recent"
    data, err = _fetch_json(url)
    if err:
        result = {"error": err}
        if "429" in err:
            result["note"] = "pypistats.org rate-limited; retry after a few minutes"
        return result
    d = data.get("data", {})
    return {
        "downloads_last_day": d.get("last_day"),
        "downloads_last_week": d.get("last_week"),
        "downloads_last_month": d.get("last_month"),
        "version_split_note": (
            "Per-version counts require BigQuery (pypistats.org does not expose them). "
            "To check v4 pickup specifically, compare release-date-filtered BigQuery results."
        ),
    }


def _collect_pypi_versions() -> list[dict]:
    """Top-10 versions by recency from PyPI JSON API."""
    url = f"https://pypi.org/pypi/{PACKAGE}/json"
    data, err = _fetch_json(url)
    if err:
        return [{"error": err}]
    releases = data.get("releases", {})
    versions = []
    for ver, files in releases.items():
        if not files:
            continue
        upload_time = sorted(f.get("upload_time", "") for f in files)[-1]
        versions.append({"version": ver, "released": upload_time})
    versions.sort(key=lambda x: x["released"], reverse=True)
    return versions[:10]


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def collect_metrics(token: str | None = None, *, now: datetime | None = None) -> dict:
    collected_at = now or datetime.now(timezone.utc)
    return {
        "snapshot_at": collected_at.isoformat(),
        "repo": REPO,
        "package": PACKAGE,
        "github": _collect_github(token),
        "github_traffic": _collect_traffic(token),
        "pypi": _collect_pypi_recent(),
        "pypi_versions": _collect_pypi_versions(),
    }


def collection_errors(metrics: dict, *, require_traffic: bool = False) -> list[str]:
    """Return human-readable collector failures (empty if the snapshot is complete).

    ``require_traffic=True`` (``--strict`` / GitHub Actions) also treats a
    skipped or empty traffic section as a failure so the daily workflow cannot
    commit N/A clones/visitors as a successful snapshot.
    """
    errors: list[str] = []
    gh = metrics.get("github") or {}
    if gh.get("error"):
        errors.append(f"github: {gh['error']}")
    traffic = metrics.get("github_traffic") or {}
    for key in ("error", "clones_error", "views_error"):
        if traffic.get(key):
            errors.append(f"github_traffic.{key}: {traffic[key]}")
    if require_traffic:
        if traffic.get("note"):
            errors.append(f"github_traffic: {traffic['note']}")
        elif traffic.get("clones_14d") is None or traffic.get("views_14d") is None:
            errors.append("github_traffic: clones/views missing from snapshot")
        elif not traffic.get("clones_daily") or not traffic.get("views_daily"):
            errors.append(
                "github_traffic: daily series missing "
                "(need per=day clones/views to reconstruct period totals)"
            )
    pypi = metrics.get("pypi") or {}
    if pypi.get("error"):
        errors.append(f"pypi: {pypi['error']}")
    versions = metrics.get("pypi_versions") or []
    if versions and isinstance(versions[0], dict) and versions[0].get("error"):
        errors.append(f"pypi_versions: {versions[0]['error']}")
    return errors


# ---------------------------------------------------------------------------
# Period reconstruction (GitHub traffic is a rolling 14-day window)
# ---------------------------------------------------------------------------


def _snapshot_day(snapshot: dict) -> str:
    return str(snapshot.get("snapshot_at") or "")[:10]


def _days_in_range(start: str, end: str) -> list[str]:
    try:
        s = date.fromisoformat(start)
        e = date.fromisoformat(end)
    except ValueError:
        return []
    if e < s:
        return []
    days: list[str] = []
    d = s
    while d <= e:
        days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def load_snapshots(metrics_dir: Path) -> list[dict]:
    """Load ``adoption-YYYY-MM-DD.json`` files; skip unreadable ones."""
    snapshots: list[dict] = []
    if not metrics_dir.is_dir():
        return snapshots
    for path in sorted(metrics_dir.glob("adoption-*.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            snapshots.append(data)
    return snapshots


def complete_period_end(end: str, *, now: date | None = None) -> tuple[str, str | None]:
    """Inclusive period end with the collection-day dropped if still open.

    GitHub Traffic rows for the snapshot's UTC day are still accumulating
    at collection time. Default ``today`` to that snapshot day — do **not**
    re-read the clock. Collection that starts before UTC midnight and
    finishes after would otherwise see ``end != datetime.now().date()`` and
    publish the still-partial collection-day row as a complete-period total.

    Pass ``now`` to treat a historical snapshot as complete (``end < now``).
    Historical ends are unchanged.

    Returns ``(closed_end, excluded_day_or_None)``.
    """
    try:
        end_day = date.fromisoformat(end)
    except ValueError:
        return end, None
    today = now if now is not None else end_day
    today_s = today.isoformat()
    if end == today_s:
        closed = (today - timedelta(days=1)).isoformat()
        return closed, today_s
    return end, None


def reconstruct_period_counts(
    snapshots: list[dict],
    start_date: str,
    end_date: str,
    series_field: str,
) -> dict:
    """Union daily clone/view *counts* across snapshots for ``[start, end]``.

    Same-day rows take the max count (later snapshots complete "today").
    Unique counts are not reconstructed — they are not additive across days.
    Callers that want a closed period should pass ``complete_period_end()``.
    """
    by_day: dict[str, int] = {}
    for snap in snapshots:
        traffic = snap.get("github_traffic") or {}
        for row in traffic.get(series_field) or []:
            if not isinstance(row, dict):
                continue
            day = str(row.get("date") or "")[:10]
            if len(day) != 10 or not (start_date <= day <= end_date):
                continue
            try:
                n = int(row["count"])
            except (KeyError, TypeError, ValueError):
                continue
            prev = by_day.get(day)
            by_day[day] = n if prev is None else max(prev, n)

    span_days = _days_in_range(start_date, end_date)
    missing = [d for d in span_days if d not in by_day]
    return {
        "total": sum(by_day.values()) if by_day else None,
        "days_covered": len(by_day),
        "days_span": len(span_days),
        "missing_days": missing,
    }


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def _md_table(headers: list[str], rows: list[list]) -> str:
    def fmt(v):
        return "N/A" if v is None else str(v)

    lines = ["| " + " | ".join(headers) + " |", "|" + " --- |" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(lines)


def format_markdown(m: dict) -> str:
    gh = m.get("github", {})
    traffic = m.get("github_traffic", {})
    pypi = m.get("pypi", {})
    versions = m.get("pypi_versions", [])

    sections = [
        f"# uniswap-python Adoption Snapshot",
        f"",
        f"**Snapshot date**: {m['snapshot_at']}",
        f"",
        f"## GitHub",
        f"",
        _md_table(
            ["Metric", "Value"],
            [
                ["Stars", gh.get("stars", "N/A")],
                ["Forks", gh.get("forks", "N/A")],
                ["Watchers", gh.get("watchers", "N/A")],
                ["Open Issues", gh.get("open_issues", "N/A")],
            ],
        ),
        f"",
        f"## GitHub Traffic (14-day window)",
        f"",
    ]

    traffic_err = traffic.get("error") or traffic.get("clones_error") or traffic.get("views_error")
    if "note" in traffic and not traffic_err:
        sections += [f"_{traffic['note']}_", ""]
    elif traffic_err:
        sections += [f"_Error: {traffic_err}_", ""]
    else:
        sections += [
            _md_table(
                ["Metric", "Value"],
                [
                    ["Clones (14d)", traffic.get("clones_14d", "N/A")],
                    ["Unique Cloners (14d)", traffic.get("unique_cloners_14d", "N/A")],
                    ["Views (14d)", traffic.get("views_14d", "N/A")],
                    ["Unique Visitors (14d)", traffic.get("unique_visitors_14d", "N/A")],
                    [
                        "Daily series stored",
                        f"{len(traffic.get('clones_daily') or [])} clone-days / "
                        f"{len(traffic.get('views_daily') or [])} view-days",
                    ],
                ],
            ),
            "",
        ]

    sections += [
        f"## PyPI Downloads",
        f"",
        _md_table(
            ["Period", "Downloads"],
            [
                ["Last day", pypi.get("downloads_last_day", "N/A")],
                ["Last week", pypi.get("downloads_last_week", "N/A")],
                ["Last month", pypi.get("downloads_last_month", "N/A")],
            ],
        ),
        f"",
        f"_{pypi.get('version_split_note') or pypi.get('note', '')}_",
        f"",
        f"## Recent Releases",
        f"",
        _md_table(
            ["Version", "Released"],
            [[v.get("version", "?"), v.get("released", "?")[:10]] for v in versions[:5]],
        ),
        f"",
    ]

    return "\n".join(sections)


def _delta(old, new) -> str:
    if old is None or new is None:
        return "N/A"
    try:
        d = int(new) - int(old)
        return f"+{d}" if d >= 0 else str(d)
    except (TypeError, ValueError):
        return "N/A"


def _format_traffic_report(
    baseline: dict,
    current: dict,
    snapshots: list[dict] | None,
    *,
    now: date | None = None,
) -> list[str]:
    """Traffic section: reconstruct period counts; never subtract 14d windows."""
    start = _snapshot_day(baseline)
    raw_end = _snapshot_day(current)
    end, partial_day = complete_period_end(raw_end, now=now)
    all_snaps = list(snapshots or [])
    all_snaps.extend([baseline, current])

    clones = reconstruct_period_counts(all_snaps, start, end, "clones_daily")
    views = reconstruct_period_counts(all_snaps, start, end, "views_daily")
    bt = baseline.get("github_traffic") or {}
    ct = current.get("github_traffic") or {}

    lines = [
        "## GitHub Traffic",
        "",
        "GitHub's Traffic API retains **14 days**. The `*_14d` fields are rolling",
        "windows, not cumulative counters — they are **not subtracted** (a later",
        "window minus an earlier one is not period traffic).",
        "Period clone/view totals are reconstructed by unioning the daily series",
        "stored in each snapshot. The current UTC day is excluded — its row is",
        "still accumulating.",
        "",
    ]

    empty_complete_window = bool(partial_day) and end < start
    no_series = clones["days_covered"] == 0 and views["days_covered"] == 0

    if empty_complete_window:
        lines += [
            f"_No complete UTC days in {start} → {raw_end} yet. "
            f"{partial_day} is still accumulating and is excluded from "
            f"period totals._",
            "",
        ]
    elif no_series:
        lines += [
            "_Period totals unavailable — snapshots do not yet contain a daily "
            "traffic series. After the PAT secret is set, each daily run stores "
            "the 14-day breakdown so D4 can reconstruct the grant window._",
            "",
        ]
    else:
        lines += [
            f"### Period totals ({start} → {end})",
            "",
            _md_table(
                ["Metric", "Total", "Coverage"],
                [
                    [
                        "Clones",
                        clones["total"],
                        f"{clones['days_covered']}/{clones['days_span']} days",
                    ],
                    [
                        "Views",
                        views["total"],
                        f"{views['days_covered']}/{views['days_span']} days",
                    ],
                ],
            ),
            "",
        ]
        if partial_day:
            lines += [
                f"_{partial_day} excluded — GitHub Traffic for the current "
                f"UTC day is still accumulating._",
                "",
            ]
        missing = sorted(set(clones["missing_days"] + views["missing_days"]))
        if missing:
            shown = missing[:12]
            extra = f" (+{len(missing) - 12} more)" if len(missing) > 12 else ""
            lines += [f"_Gaps: {', '.join(shown)}{extra}_", ""]
        lines += [
            "Unique cloners/visitors are **not additive** across days and cannot "
            "be reconstructed as a period total.",
            "",
        ]

    lines += [
        "### Rolling 14-day windows (point-in-time, not a period delta)",
        "",
        _md_table(
            ["Metric", "Baseline (14d)", "Current (14d)"],
            [
                ["Clones", bt.get("clones_14d", "N/A"), ct.get("clones_14d", "N/A")],
                [
                    "Unique cloners",
                    bt.get("unique_cloners_14d", "N/A"),
                    ct.get("unique_cloners_14d", "N/A"),
                ],
                ["Views", bt.get("views_14d", "N/A"), ct.get("views_14d", "N/A")],
                [
                    "Unique visitors",
                    bt.get("unique_visitors_14d", "N/A"),
                    ct.get("unique_visitors_14d", "N/A"),
                ],
            ],
        ),
        "",
    ]
    return lines


def format_report(
    baseline: dict,
    current: dict,
    snapshots: list[dict] | None = None,
    *,
    now: date | None = None,
) -> str:
    bg = baseline.get("github", {})
    cg = current.get("github", {})
    bp = baseline.get("pypi", {})
    cp = current.get("pypi", {})

    sections = [
        "# uniswap-python Adoption Report — Deltas",
        "",
        f"Baseline: {baseline['snapshot_at']}",
        f"Current:  {current['snapshot_at']}",
        "",
        "## GitHub",
        "",
        _md_table(
            ["Metric", "Baseline", "Current", "Delta"],
            [
                ["Stars", bg.get("stars", "N/A"), cg.get("stars", "N/A"), _delta(bg.get("stars"), cg.get("stars"))],
                ["Forks", bg.get("forks", "N/A"), cg.get("forks", "N/A"), _delta(bg.get("forks"), cg.get("forks"))],
                ["Watchers", bg.get("watchers", "N/A"), cg.get("watchers", "N/A"), _delta(bg.get("watchers"), cg.get("watchers"))],
            ],
        ),
        "",
        *_format_traffic_report(baseline, current, snapshots, now=now),
        "## PyPI Downloads",
        "",
        "_PyPI day/week/month figures are also rolling windows; deltas below "
        "compare two windows, not downloads accumulated over the grant period._",
        "",
        _md_table(
            ["Period", "Baseline", "Current", "Window delta"],
            [
                ["Last day", bp.get("downloads_last_day", "N/A"), cp.get("downloads_last_day", "N/A"),
                 _delta(bp.get("downloads_last_day"), cp.get("downloads_last_day"))],
                ["Last week", bp.get("downloads_last_week", "N/A"), cp.get("downloads_last_week", "N/A"),
                 _delta(bp.get("downloads_last_week"), cp.get("downloads_last_week"))],
                ["Last month", bp.get("downloads_last_month", "N/A"), cp.get("downloads_last_month", "N/A"),
                 _delta(bp.get("downloads_last_month"), cp.get("downloads_last_month"))],
            ],
        ),
        "",
    ]

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _token_from_env() -> str | None:
    return os.environ.get("ADOPTION_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN") or None


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--out", default="metrics", help="Output directory (default: metrics/)")
    parser.add_argument(
        "--report",
        metavar="BASELINE.json",
        help="Report mode: compute deltas vs baseline snapshot",
    )
    parser.add_argument(
        "--metrics-dir",
        default=None,
        help="Directory of adoption-*.json snapshots used to reconstruct "
        "period traffic (default: directory of --report)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any collector failed (default in GitHub Actions)",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write snapshot and exit 0 even if some collectors failed",
    )
    args = parser.parse_args()

    token = _token_from_env()
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    strict = (args.strict or in_actions) and not args.allow_partial
    # One clock for snapshot_at, filename, and period-end exclusion so a
    # midnight boundary during network I/O cannot desynchronize them.
    collected_at = datetime.now(timezone.utc)

    if args.report:
        baseline_path = Path(args.report)
        if not baseline_path.exists():
            print(f"ERROR: Baseline file not found: {baseline_path}", file=sys.stderr)
            sys.exit(1)
        baseline = json.loads(baseline_path.read_text())
        current = collect_metrics(token, now=collected_at)
        metrics_dir = Path(args.metrics_dir) if args.metrics_dir else baseline_path.parent
        snapshots = load_snapshots(metrics_dir)
        print(format_report(baseline, current, snapshots, now=collected_at.date()))
        errors = collection_errors(current, require_traffic=strict)
        if errors:
            print("Collector errors:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            if strict:
                sys.exit(1)
        return

    metrics = collect_metrics(token, now=collected_at)
    errors = collection_errors(metrics, require_traffic=strict)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    date_str = collected_at.strftime("%Y-%m-%d")
    json_path = out_dir / f"adoption-{date_str}.json"
    md_path = out_dir / f"adoption-{date_str}.md"

    json_path.write_text(json.dumps(metrics, indent=2) + "\n")
    md_path.write_text(format_markdown(metrics))

    print(f"Snapshot written:\n  JSON: {json_path}\n  Markdown: {md_path}\n")

    gh = metrics.get("github", {})
    pypi = metrics.get("pypi", {})
    print(f"Stars: {gh.get('stars', 'N/A')}  Forks: {gh.get('forks', 'N/A')}  "
          f"PyPI/month: {pypi.get('downloads_last_month', 'N/A')}")

    if errors:
        print("Collector errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        if strict:
            sys.exit(1)


if __name__ == "__main__":
    main()
