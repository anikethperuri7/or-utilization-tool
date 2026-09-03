import math

import pytest

from or_utilization.metrics import compute_metrics


def test_case_level_delay_and_overrun(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    case_level = m.case_level.sort_values("scheduled_start_dt").reset_index(drop=True)

    # Case 1: start_delay 10 min, overrun 20 min
    assert math.isclose(case_level.loc[0, "start_delay_min"], 10.0)
    assert math.isclose(case_level.loc[0, "overrun_min_clipped"], 20.0)

    # Case 2: cancelled -> delay/overrun are NaN
    assert case_level.loc[1, "status"] == "cancelled"
    assert math.isnan(case_level.loc[1, "start_delay_min"])

    # Case 3: start_delay 15 min, finished early so overrun clipped to 0
    assert math.isclose(case_level.loc[2, "start_delay_min"], 15.0)
    assert math.isclose(case_level.loc[2, "overrun_min_clipped"], 0.0)
    assert math.isclose(case_level.loc[2, "early_finish_min_clipped"], 15.0)


def test_daily_room_summary_utilization(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    row = m.daily_room_summary.iloc[0]

    assert row["room_id"] == "OR-TEST"
    assert math.isclose(row["block_minutes"], 300.0)  # 07:00-12:00
    assert math.isclose(row["occupied_minutes"], 100.0)  # 70 + 30
    assert math.isclose(row["idle_minutes"], 200.0)
    assert math.isclose(row["utilization_pct"], 100.0 / 300.0 * 100.0)
    assert row["n_scheduled"] == 3
    assert row["n_completed"] == 2
    assert row["n_cancelled"] == 1
    assert math.isclose(row["cancellation_rate_pct"], 1 / 3 * 100)


def test_turnaround_time_between_completed_cases(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    # Only one gap exists: case1 ends 08:20, case3 (next completed) starts 09:30 -> 70 min
    assert len(m.turnaround_times) == 1
    assert math.isclose(m.turnaround_times.iloc[0]["turnaround_min"], 70.0)


def test_surgeon_summary_groups_correctly(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    surgeons = set(m.surgeon_summary["surgeon_id"])
    assert surgeons == {"SUR-TEST-1", "SUR-TEST-2"}

    sur1 = m.surgeon_summary[m.surgeon_summary["surgeon_id"] == "SUR-TEST-1"].iloc[0]
    assert sur1["n_scheduled"] == 2  # case 1 (completed) + case 2 (cancelled)
    assert sur1["n_completed"] == 1
    assert sur1["n_cancelled"] == 1


def test_overall_summary_matches_expected_values(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    o = m.overall

    assert o["n_cases_scheduled"] == 3
    assert o["n_cases_completed"] == 2
    assert o["n_cases_cancelled"] == 1
    assert math.isclose(o["cancellation_rate_pct"], 1 / 3 * 100)
    assert math.isclose(o["overall_utilization_pct"], 100.0 / 300.0 * 100.0)
    assert math.isclose(o["avg_turnaround_min"], 70.0)
