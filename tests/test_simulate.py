import math

import pandas as pd
import pytest

from or_utilization.metrics import compute_metrics
from or_utilization.simulate import simulate_schedule_optimization, compare_scenarios


def test_zero_improvement_scenario_reclaims_nothing(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    sim = simulate_schedule_optimization(
        m.daily_room_summary,
        turnaround_reduction_min=0,
        start_delay_reduction_pct=0,
        overrun_reduction_pct=0,
        scenario_name="baseline",
    )
    assert sim.summary["total_reclaimed_minutes"] == 0.0
    assert sim.summary["est_additional_cases_from_efficiency_only"] == 0.0


def test_turnaround_reduction_reclaims_expected_minutes(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    # 2 completed cases -> 1 turnaround gap in the room-day
    sim = simulate_schedule_optimization(
        m.daily_room_summary,
        turnaround_reduction_min=10,
        start_delay_reduction_pct=0,
        overrun_reduction_pct=0,
        scenario_name="turnaround_only",
    )
    row = sim.room_day_detail.iloc[0]
    assert row["est_turnaround_gaps"] == 1
    assert math.isclose(row["reclaimed_from_turnaround_min"], 10.0)


def test_avg_case_length_defaults_when_not_supplied(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    sim = simulate_schedule_optimization(m.daily_room_summary, scenario_name="default_case_len")
    # occupied 100 min over 2 completed cases -> 50 min avg
    assert math.isclose(sim.assumptions["avg_case_length_min"], 50.0)


def test_avg_case_length_can_be_overridden(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    sim = simulate_schedule_optimization(
        m.daily_room_summary, avg_case_length_min=25.0, scenario_name="override"
    )
    assert sim.assumptions["avg_case_length_min"] == 25.0


def test_compare_scenarios_returns_one_row_per_scenario(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    sim1 = simulate_schedule_optimization(m.daily_room_summary, scenario_name="A")
    sim2 = simulate_schedule_optimization(
        m.daily_room_summary, turnaround_reduction_min=15, scenario_name="B"
    )
    cmp_df = compare_scenarios([sim1, sim2])
    assert len(cmp_df) == 2
    assert set(cmp_df["scenario_name"]) == {"A", "B"}


def test_reclaimed_minutes_never_negative(tiny_schedule_df):
    m = compute_metrics(tiny_schedule_df)
    sim = simulate_schedule_optimization(
        m.daily_room_summary,
        turnaround_reduction_min=5,
        start_delay_reduction_pct=50,
        overrun_reduction_pct=50,
        scenario_name="sanity",
    )
    assert (sim.room_day_detail["total_reclaimed_min"] >= 0).all()
