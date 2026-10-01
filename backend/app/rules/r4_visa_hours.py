"""R4 student-visa work-hours check."""

from __future__ import annotations

from datetime import date, timedelta

from app.config import Config
from app.models import Check, Severity, Worker


def rolling_windows(
    hours_by_day: dict[date, float],
    start: date,
    end: date,
    *,
    limit: float = 48,
    warn: float = 44,
    days: int = 14,
) -> list[tuple[date, date, float, str]]:
    """Return qualifying inclusive daily windows, advancing one day at a time."""
    if days < 1:
        raise ValueError("days must be positive")

    windows: list[tuple[date, date, float, str]] = []
    window_start = start
    last_start = end - timedelta(days=days - 1)
    while window_start <= last_start:
        window_end = window_start + timedelta(days=days - 1)
        total = sum(hours_by_day.get(window_start + timedelta(days=offset), 0) for offset in range(days))
        if total >= warn:
            windows.append((window_start, window_end, total, "over" if total > limit else "near"))
        window_start += timedelta(days=1)
    return windows


def _in_course_break(day: date, cfg: Config) -> bool:
    return any(start <= day <= end for start, end in cfg.course_breaks)


def _display_hours(hours: float) -> float | int:
    return int(hours) if float(hours).is_integer() else hours


def _merge_windows(
    windows: list[tuple[date, date, float, str]],
) -> list[list[tuple[date, date, float, str]]]:
    """Merge overlapping windows, including chains of pairwise overlaps."""
    groups: list[list[tuple[date, date, float, str]]] = []
    for window in windows:
        if not groups or window[0] > groups[-1][-1][1]:
            groups.append([window])
        else:
            groups[-1].append(window)
    return groups


def run(worker: Worker, cfg: Config) -> list[Check]:
    """Warn Visa 500 holders when planned work makes a future window near/full."""
    if worker.visa != "500":
        return []

    planned_shifts = [shift for shift in worker.shifts if shift.planned]
    if not planned_shifts:
        return []

    hours_by_day: dict[date, float] = {}
    for shift in worker.shifts:
        if not _in_course_break(shift.date, cfg):
            hours_by_day[shift.date] = hours_by_day.get(shift.date, 0) + shift.hours
    for platform_day in worker.platform_days:
        if not _in_course_break(platform_day.date, cfg):
            hours_by_day[platform_day.date] = (
                hours_by_day.get(platform_day.date, 0) + platform_day.online_minutes / 60
            )

    last_planned_date = max(shift.date for shift in planned_shifts)
    scan_start = worker.today - timedelta(days=cfg.visa_window_days - 1)
    qualifying = [
        window
        for window in rolling_windows(
            hours_by_day,
            scan_start,
            last_planned_date,
            limit=cfg.visa_limit_hours,
            warn=cfg.visa_warn_hours,
            days=cfg.visa_window_days,
        )
        if window[1] > worker.today
    ]

    checks: list[Check] = []
    for group in _merge_windows(qualifying):
        # ``max`` keeps the earliest window where totals are tied: groups are chronological.
        window_start, window_end, total, status = max(group, key=lambda window: window[2])
        contributing_planned = [
            {
                "date": shift.date.isoformat(),
                "source_id": shift.source_id,
                "hours": _display_hours(shift.hours),
            }
            for shift in sorted(planned_shifts, key=lambda shift: (shift.date, shift.source_id))
            if window_start <= shift.date <= window_end and not _in_course_break(shift.date, cfg)
        ]
        title = (
            f"Planned shifts may take you over {cfg.visa_limit_hours} hours in {cfg.visa_window_days} days"
            if status == "over"
            else f"Planned shifts may take you near {cfg.visa_limit_hours} hours in {cfg.visa_window_days} days"
        )
        checks.append(
            Check(
                check_id=f"r4-all-{window_start.isoformat()}",
                rule="R4",
                severity=Severity.warning,
                title=title,
                period_start=window_start,
                period_end=window_end,
                facts={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "total_hours": _display_hours(total),
                    "limit_hours": cfg.visa_limit_hours,
                    "warn_hours": cfg.visa_warn_hours,
                    "status": status,
                    "planned_shifts": contributing_planned,
                    "counts_platform_online_time": True,
                },
                possible_explanations=[
                    "Some planned shifts may still change.",
                    "Platform online time is counted conservatively; the official method may count fewer hours.",
                ],
                next_steps=[
                    "Adjust next week's roster so no 14-day window goes over 48 hours.",
                    "Check the Home Affairs work-hours rules for student visas.",
                ],
            )
        )
    return checks
