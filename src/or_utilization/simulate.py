"""
simulate.py
-----------
Simulates schedule-optimization scenarios against historical room-day data
to estimate how many additional procedures could theoretically be fit into
existing block/operating hours, without extending them.

Approach
--------
For each room-day, we know:
    - block_minutes        : total available time
    - occupied_minutes      : time actually used by completed cases
    - idle_minutes           : block_minutes - occupied_minutes
    - avg_turnaround_min      : observed gap between cases in that room
    - overrun / start-delay   : inefficiencies eating into idle time

We model three levers a scheduler could realistically pull, and estimate
the "reclaimed minutes" from each:

  1. Turnaround reduction  : tightening turnover time (e.g. parallel
                              room-cleaning workflows, pre-staged supplies)
                              reduces the gap between cases.
  2. Start-delay reduction : reducing first-case-of-day and cascading
                              delays reclaims time lost to late starts.
  3. Overrun reduction     : better case-length estimation / block
                              discipline reduces cases running over,
                              which reduces downstream cascading delay.

Reclaimed minutes are pooled per room-day and divided by a representative
average case length (either supplied or derived from the historical data)
to estimate the number of *additional* procedures that could be scheduled
in that same room-day without lengthening operating hours.

This is a deliberately transparent, assumption-driven heuristic model
(not a queueing/discrete-event simulation) so that every number in the
output can be traced back to an input assumption. It's meant to support
"what would happen if..." conversations with OR leadership, not to be
a black box.
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class SimulationResult:
    scenario_name: str
    assumptions: dict
    room_day_detail: pd.DataFrame
    summary: dict


def simulate_schedule_optimization(
    daily_room_summary: pd.DataFrame,
    turnaround_reduction_min: float = 0.0,
    start_delay_reduction_pct: float = 0.0,
    overrun_reduction_pct: float = 0.0,
    avg_case_length_min: float | None = None,
    cases_per_room_day: float | None = None,
    scenario_name: str = "custom_scenario",
) -> SimulationResult:
    """
    Simulate the effect of process improvements on room capacity.

    Parameters
    ----------
    daily_room_summary : pd.DataFrame
        Output of metrics.compute_metrics(...).daily_room_summary
    turnaround_reduction_min : float
        Minutes shaved off *each* turnaround gap per completed-case
        transition in a room-day (e.g. 10 = "turnaround improves by 10 min").
    start_delay_reduction_pct : float
        Percent (0-100) reduction applied to each room-day's average
        start delay, reclaimed as usable time.
    overrun_reduction_pct : float
        Percent (0-100) reduction applied to each room-day's total
        overrun minutes, reclaimed as usable time.
    avg_case_length_min : float, optional
        Representative case length used to convert reclaimed minutes into
        an estimated case count. Defaults to the dataset's mean
        actual case duration if not provided.
    cases_per_room_day : float, optional
        Average completed cases per room-day, used to estimate how many
        turnaround gaps exist per room-day if not directly observable.
        Defaults to the dataset's observed mean.
    scenario_name : str
        Label for this scenario, useful when comparing multiple runs.

    Returns
    -------
    SimulationResult
    """
    df = daily_room_summary.copy()

    if avg_case_length_min is None:
        # Fall back to a reasonable derived default from occupied time / case count
        total_occupied = df["occupied_minutes"].sum()
        total_completed = df["n_completed"].sum()
        avg_case_length_min = (
            total_occupied / total_completed if total_completed else np.nan
        )

    if cases_per_room_day is None:
        cases_per_room_day = df["n_completed"].mean()

    # Number of turnaround "gaps" in a room-day ~= n_completed - 1 (if >=1 case)
    df["est_turnaround_gaps"] = (df["n_completed"] - 1).clip(lower=0)

    # --- Reclaimed minutes from each lever ---
    df["reclaimed_from_turnaround_min"] = (
        df["est_turnaround_gaps"] * turnaround_reduction_min
    )
    df["reclaimed_from_start_delay_min"] = (
        df["avg_start_delay_min"].fillna(0).clip(lower=0)
        * (start_delay_reduction_pct / 100.0)
    )
    df["reclaimed_from_overrun_min"] = (
        df["total_overrun_min"].fillna(0) * (overrun_reduction_pct / 100.0)
    )

    df["total_reclaimed_min"] = (
        df["reclaimed_from_turnaround_min"]
        + df["reclaimed_from_start_delay_min"]
        + df["reclaimed_from_overrun_min"]
    )

    # Also recapture idle time already present as "available" capacity,
    # reported separately so it's not conflated with *newly reclaimed* time.
    df["existing_idle_min"] = df["idle_minutes"].fillna(0)

    df["est_additional_cases"] = (
        df["total_reclaimed_min"] / avg_case_length_min
        if avg_case_length_min and avg_case_length_min > 0
        else np.nan
    )
    df["est_additional_cases_incl_existing_idle"] = (
        (df["total_reclaimed_min"] + df["existing_idle_min"]) / avg_case_length_min
        if avg_case_length_min and avg_case_length_min > 0
        else np.nan
    )

    new_utilization_pct = (
        (df["occupied_minutes"] + df["total_reclaimed_min"])
        / df["block_minutes"]
        * 100.0
    )

    summary = {
        "scenario_name": scenario_name,
        "avg_case_length_min_used": round(float(avg_case_length_min), 1)
        if pd.notna(avg_case_length_min)
        else None,
        "total_reclaimed_minutes": round(float(df["total_reclaimed_min"].sum()), 1),
        "total_existing_idle_minutes": round(float(df["existing_idle_min"].sum()), 1),
        "est_additional_cases_from_efficiency_only": round(
            float(df["est_additional_cases"].sum()), 1
        ),
        "est_additional_cases_incl_existing_idle": round(
            float(df["est_additional_cases_incl_existing_idle"].sum()), 1
        ),
        "baseline_utilization_pct": round(
            float(df["utilization_pct"].mean()), 1
        ),
        "projected_utilization_pct": round(
            float(new_utilization_pct.clip(upper=100).mean()), 1
        ),
        "n_room_days_analyzed": int(df.shape[0]),
    }

    assumptions = {
        "turnaround_reduction_min_per_gap": turnaround_reduction_min,
        "start_delay_reduction_pct": start_delay_reduction_pct,
        "overrun_reduction_pct": overrun_reduction_pct,
        "avg_case_length_min": summary["avg_case_length_min_used"],
        "cases_per_room_day_assumed": round(float(cases_per_room_day), 2)
        if pd.notna(cases_per_room_day)
        else None,
    }

    return SimulationResult(
        scenario_name=scenario_name,
        assumptions=assumptions,
        room_day_detail=df,
        summary=summary,
    )


def compare_scenarios(results: list[SimulationResult]) -> pd.DataFrame:
    """Build a side-by-side comparison table from multiple SimulationResults."""
    rows = []
    for r in results:
        row = {"scenario_name": r.scenario_name}
        row.update(r.summary)
        row.update({f"assump_{k}": v for k, v in r.assumptions.items()})
        rows.append(row)
    return pd.DataFrame(rows)
