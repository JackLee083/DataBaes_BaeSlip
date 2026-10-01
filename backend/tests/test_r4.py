from dataclasses import replace
from datetime import date

import pytest

from app.config import Config
from app.models import PlatformDay, Worker, WorkShift
from app.rules.r4_visa_hours import rolling_windows, run


def worker(
    *,
    shifts: list[WorkShift],
    platform_days: list[PlatformDay] | None = None,
    visa: str | None = "500",
    today: date = date(2026, 9, 29),
) -> Worker:
    return Worker(
        worker_id="student",
        display_name="Student",
        language="en",
        visa=visa,
        today=today,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 9, 30),
        sources=[],
        income=[],
        shifts=shifts,
        platform_days=platform_days or [],
        platform_payouts=[],
        super_contributions=[],
        bank_deposits=[],
    )


def test_planned_window_0928_1011_is_50_one_warning() -> None:
    planned = [
        (date(2026, 9, 30), 8),
        (date(2026, 10, 1), 8),
        (date(2026, 10, 3), 6),
        (date(2026, 10, 4), 4),
        (date(2026, 10, 5), 4),
        (date(2026, 10, 7), 6),
        (date(2026, 10, 9), 4),
        (date(2026, 10, 10), 6),
        (date(2026, 10, 11), 4),
    ]
    checks = run(
        worker(shifts=[
            WorkShift(date=date(2026, 9, 20), hours=2, source_id="overseas-job"),
            *[WorkShift(date=day, hours=hours, source_id="abc-cafe", planned=True) for day, hours in planned],
        ]),
        Config(),
    )

    assert len(checks) == 1
    check = checks[0]
    assert check.check_id == "r4-all-2026-09-28"
    assert check.period_start == date(2026, 9, 28)
    assert check.period_end == date(2026, 10, 11)
    assert check.severity.value == "warning"
    assert check.facts["total_hours"] == 50
    assert check.facts["status"] == "over"
    assert check.facts["planned_shifts"] == [
        {"date": day.isoformat(), "source_id": "abc-cafe", "hours": hours}
        for day, hours in planned
    ]


def test_home_affairs_trap_56_hours() -> None:
    weekly = [(date(2026, 9, 14), 15, False), (date(2026, 9, 21), 25, False),
              (date(2026, 9, 28), 31, True), (date(2026, 10, 5), 9, True)]
    hours_by_day = {day: hours for day, hours, _ in weekly}

    windows = rolling_windows(hours_by_day, date(2026, 9, 14), date(2026, 10, 11))
    assert (date(2026, 9, 21), date(2026, 10, 4), 56, "over") in windows
    assert run(
        worker(shifts=[WorkShift(date=day, hours=hours, source_id="all-work", planned=planned)
                       for day, hours, planned in weekly]),
        Config(),
    )[0].facts["total_hours"] == 56


def test_no_planned_shifts_emits_no_future_alert() -> None:
    assert run(
        worker(shifts=[WorkShift(date=date(2026, 9, 20), hours=60, source_id="job")]),
        Config(),
    ) == []


@pytest.mark.parametrize(
    ("hours", "expected_status"),
    [(43.99, None), (44, "near"), (48, "near"), (48.01, "over")],
)
def test_threshold_boundaries(hours: float, expected_status: str | None) -> None:
    checks = run(
        worker(shifts=[WorkShift(date=date(2026, 9, 30), hours=hours, source_id="job", planned=True)]),
        Config(),
    )
    if expected_status is None:
        assert checks == []
    else:
        assert checks[0].severity.value == "warning"
        assert checks[0].facts["status"] == expected_status


def test_course_break_start_boundary_is_inclusive() -> None:
    assert run(
        worker(
            today=date(2026, 6, 19),
            shifts=[
                WorkShift(date=date(2026, 6, 19), hours=1, source_id="job", planned=True),
                WorkShift(date=date(2026, 6, 20), hours=60, source_id="job", planned=True),
            ],
        ),
        Config(),
    ) == []


def test_course_break_end_boundary_is_inclusive() -> None:
    checks = run(
        worker(
            today=date(2026, 7, 13),
            shifts=[
                WorkShift(date=date(2026, 7, 26), hours=60, source_id="job", planned=True),
                WorkShift(date=date(2026, 7, 27), hours=1, source_id="job", planned=True),
            ],
        ),
        Config(),
    )
    assert checks == []


def test_platform_online_time_is_counted_conservatively() -> None:
    checks = run(
        worker(
            shifts=[WorkShift(date=date(2026, 9, 30), hours=1, source_id="job", planned=True)],
            platform_days=[PlatformDay(
                date=date(2026, 9, 30), source_id="delivery", engaged_minutes=60,
                online_minutes=2_880, gross_cents=0,
            )],
        ),
        Config(),
    )
    assert checks[0].facts["total_hours"] == 49
    assert checks[0].facts["counts_platform_online_time"] is True


def test_non_student_visa_is_not_checked() -> None:
    assert run(
        worker(
            visa="485",
            shifts=[WorkShift(date=date(2026, 9, 30), hours=50, source_id="job", planned=True)],
        ),
        Config(),
    ) == []


def test_configured_window_length_and_unpadded_scan_bound() -> None:
    cfg = replace(Config(), visa_window_days=7)
    checks = run(
        worker(shifts=[
            WorkShift(date=date(2026, 9, 22), hours=50, source_id="old", planned=True),
            WorkShift(date=date(2026, 10, 5), hours=1, source_id="latest", planned=True),
        ]),
        cfg,
    )
    assert checks == []


def test_transitively_overlapping_windows_merge_and_keep_earliest_peak() -> None:
    checks = run(
        worker(shifts=[
            WorkShift(date=date(2026, 9, 30), hours=44, source_id="job", planned=True),
            WorkShift(date=date(2026, 10, 11), hours=6, source_id="job", planned=True),
        ]),
        Config(),
    )
    assert len(checks) == 1
    assert checks[0].check_id == "r4-all-2026-09-28"
    assert checks[0].facts["total_hours"] == 50


def test_input_order_does_not_change_peak_or_planned_facts() -> None:
    shifts = [
        WorkShift(date=date(2026, 9, 30), hours=44, source_id="b", planned=True),
        WorkShift(date=date(2026, 10, 11), hours=6, source_id="a", planned=True),
    ]
    forward = run(worker(shifts=shifts), Config())
    reverse = run(worker(shifts=list(reversed(shifts))), Config())
    assert [check.model_dump() for check in forward] == [check.model_dump() for check in reverse]


def test_disjoint_qualifying_components_produce_two_checks() -> None:
    checks = run(
        worker(shifts=[
            WorkShift(date=date(2026, 9, 30), hours=44, source_id="first", planned=True),
            WorkShift(date=date(2026, 10, 28), hours=44, source_id="second", planned=True),
        ]),
        Config(),
    )
    assert [(check.period_start, check.period_end) for check in checks] == [
        (date(2026, 9, 17), date(2026, 9, 30)),
        (date(2026, 10, 15), date(2026, 10, 28)),
    ]


def test_rolling_windows_honours_configured_limit_and_days() -> None:
    assert rolling_windows(
        {date(2026, 9, 29): 10, date(2026, 9, 30): 10},
        date(2026, 9, 29),
        date(2026, 9, 30),
        limit=20,
        warn=20,
        days=2,
    ) == [(date(2026, 9, 29), date(2026, 9, 30), 20, "near")]
