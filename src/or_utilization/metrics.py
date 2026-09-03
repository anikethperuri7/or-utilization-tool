"""
metrics.py
----------
Computes the core utilization and efficiency metrics from a cleaned
schedule DataFrame (see loader.load_schedule):

- Room utilization %      : booked/occupied time vs available block time
- Turnaround time          : gap between one case's actual_end and the next
                              case's actual_start, per room
- Delay                    : actual_start - scheduled_start (first case of day
                              delay is "start-of-day delay"; later cases also
                              inherit downstream delay)
- Overrun                  : actual_end - scheduled_end (case ran long)
- Cancellation rate        : cancelled cases / total scheduled cases
- Idle time                : block time not consumed by any case
- Case-level and room/day/surgeon rollups
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class UtilizationMetrics:
    """Container for all computed metrics, each a pandas object."""

    case_level: pd.DataFrame
    daily_room_summary: pd.DataFrame
    surgeon_summary: pd.DataFrame
    turnaround_times: pd.DataFrame
    overall: dict


def _minutes(delta) -> Optional[float]:
    if pd.isna(delta):
        return np.nan
    return delta.total_seconds() / 60.0


def compute_metrics(df: pd.DataFrame) -> UtilizationMetrics:
    """
    Compute the full metrics suite from a loaded/cleaned schedule DataFrame.
    """
    df = df.copy()

    # ---- Case-level derived fields -------------------------------------
    df["scheduled_duration_min"] = (
        df["scheduled_end_dt"] - df["scheduled_start_dt"]
    ).apply(lambda x: _minutes(x))

    df["actual_duration_min"] = (df["actual_end_dt"] - df["actual_start_dt"]).apply(
        lambda x: _minutes(x)
    )

    df["start_delay_min"] = (df["actual_start_dt"] - df["scheduled_start_dt"]).apply(
        lambda x: _minutes(x)
    )

    df["overrun_min"] = (df["actual_end_dt"] - df["scheduled_end_dt"]).apply(
        lambda x: _minutes(x)
    )
    # Only count positive overrun as "overrun"; negative means finished early
    df["overrun_min_clipped"] = df["overrun_min"].clip(lower=0)
    df["early_finish_min_clipped"] = (-df["overrun_min"]).clip(lower=0)

    df["is_cancelled"] = df["status"] == "cancelled"
    df["is_completed"] = df["status"] == "completed"

    # ---- Turnaround time (gap between consecutive completed cases in a room) --
    turnaround_rows = []
    completed = df[df["is_completed"]].sort_values(
        ["room_id", "date", "actual_start_dt"]
    )
    for (room, day), grp in completed.groupby(["room_id", "date"]):
        grp = grp.sort_values("actual_start_dt").reset_index(drop=True)
        for i in range(len(grp) - 1):
            end_prev = grp.loc[i, "actual_end_dt"]
            start_next = grp.loc[i + 1, "actual_start_dt"]
            if pd.isna(end_prev) or pd.isna(start_next):
                continue
            gap_min = _minutes(start_next - end_prev)
            turnaround_rows.append(
                {
                    "room_id": room,
                    "date": day,
                    "case_before": grp.loc[i, "procedure_type"],
                    "case_after": grp.loc[i + 1, "procedure_type"],
                    "turnaround_min": gap_min,
                }
            )
    turnaround_times = pd.DataFrame(turnaround_rows)

    # ---- Daily room summary: utilization, idle time, case counts --------
    room_day_rows = []
    for (room, day), grp in df.groupby(["room_id", "date"]):
        block_start = grp["block_start_dt"].min()
        block_end = grp["block_end_dt"].max()
        block_minutes = (
            _minutes(block_end - block_start)
            if pd.notna(block_start) and pd.notna(block_end)
            else np.nan
        )

        completed_grp = grp[grp["is_completed"]]
        occupied_minutes = completed_grp["actual_duration_min"].sum()

        n_scheduled = len(grp)
        n_completed = completed_grp.shape[0]
        n_cancelled = grp["is_cancelled"].sum()

        utilization_pct = (
            (occupied_minutes / block_minutes * 100.0)
            if block_minutes and block_minutes > 0
            else np.nan
        )

        idle_minutes = (
            max(block_minutes - occupied_minutes, 0)
            if pd.notna(block_minutes)
            else np.nan
        )

        day_turnarounds = turnaround_times[
            (turnaround_times["room_id"] == room) & (turnaround_times["date"] == day)
        ]

        room_day_rows.append(
            {
                "room_id": room,
                "date": day,
                "block_minutes": block_minutes,
                "occupied_minutes": occupied_minutes,
                "idle_minutes": idle_minutes,
                "utilization_pct": utilization_pct,
                "n_scheduled": n_scheduled,
                "n_completed": n_completed,
                "n_cancelled": n_cancelled,
                "cancellation_rate_pct": (
                    (n_cancelled / n_scheduled * 100.0) if n_scheduled else np.nan
                ),
                "avg_start_delay_min": completed_grp["start_delay_min"].mean(),
                "avg_overrun_min": completed_grp["overrun_min_clipped"].mean(),
                "avg_turnaround_min": (
                    day_turnarounds["turnaround_min"].mean()
                    if not day_turnarounds.empty
                    else np.nan
                ),
                "total_overrun_min": completed_grp["overrun_min_clipped"].sum(),
            }
        )
    daily_room_summary = (
        pd.DataFrame(room_day_rows)
        .sort_values(["room_id", "date"])
        .reset_index(drop=True)
    )

    # ---- Surgeon summary --------------------------------------------------
    surgeon_rows = []
    for surgeon, grp in df.groupby("surgeon_id"):
        completed_grp = grp[grp["is_completed"]]
        n_scheduled = len(grp)
        n_cancelled = grp["is_cancelled"].sum()
        surgeon_rows.append(
            {
                "surgeon_id": surgeon,
                "n_scheduled": n_scheduled,
                "n_completed": completed_grp.shape[0],
                "n_cancelled": n_cancelled,
                "cancellation_rate_pct": (
                    (n_cancelled / n_scheduled * 100.0) if n_scheduled else np.nan
                ),
                "avg_start_delay_min": completed_grp["start_delay_min"].mean(),
                "avg_overrun_min": completed_grp["overrun_min_clipped"].mean(),
                "avg_scheduled_duration_min": grp["scheduled_duration_min"].mean(),
                "avg_actual_duration_min": completed_grp["actual_duration_min"].mean(),
                "median_case_accuracy_pct": (
                    (
                        completed_grp["scheduled_duration_min"]
                        / completed_grp["actual_duration_min"]
                        * 100
                    )
                    .replace([np.inf, -np.inf], np.nan)
                    .median()
                ),
            }
        )
    surgeon_summary = (
        pd.DataFrame(surgeon_rows)
        .sort_values("n_scheduled", ascending=False)
        .reset_index(drop=True)
    )

    # ---- Overall summary ----------------------------------------------
    total_block_minutes = daily_room_summary["block_minutes"].sum()
    total_occupied_minutes = daily_room_summary["occupied_minutes"].sum()
    overall = {
        "n_room_days": daily_room_summary.shape[0],
        "n_cases_scheduled": int(df.shape[0]),
        "n_cases_completed": int(df["is_completed"].sum()),
        "n_cases_cancelled": int(df["is_cancelled"].sum()),
        "cancellation_rate_pct": float(df["is_cancelled"].mean() * 100.0),
        "overall_utilization_pct": (
            float(total_occupied_minutes / total_block_minutes * 100.0)
            if total_block_minutes
            else np.nan
        ),
        "total_block_minutes": float(total_block_minutes),
        "total_occupied_minutes": float(total_occupied_minutes),
        "total_idle_minutes": float(daily_room_summary["idle_minutes"].sum()),
        "avg_start_delay_min": float(
            df.loc[df["is_completed"], "start_delay_min"].mean()
        ),
        "avg_overrun_min": float(
            df.loc[df["is_completed"], "overrun_min_clipped"].mean()
        ),
        "avg_turnaround_min": (
            float(turnaround_times["turnaround_min"].mean())
            if not turnaround_times.empty
            else np.nan
        ),
        "pct_cases_overrun": float(
            (df.loc[df["is_completed"], "overrun_min_clipped"] > 0).mean() * 100.0
        ),
    }

    return UtilizationMetrics(
        case_level=df,
        daily_room_summary=daily_room_summary,
        surgeon_summary=surgeon_summary,
        turnaround_times=turnaround_times,
        overall=overall,
    )
