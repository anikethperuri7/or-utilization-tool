"""
loader.py
---------
Loads and validates procedure-room scheduling data from CSV into a clean
pandas DataFrame with derived time fields used by the rest of the toolkit.

Expected input columns (case-insensitive, flexible order):
    room_id            - str, room/OR identifier (e.g. "OR-1")
    date               - str/date, the schedule date
    scheduled_start     - str/time, planned start time (HH:MM)
    scheduled_end       - str/time, planned end time (HH:MM)
    actual_start        - str/time, actual start time (HH:MM), blank if cancelled
    actual_end          - str/time, actual end time (HH:MM), blank if cancelled
    procedure_type       - str, e.g. "Total Knee Arthroplasty"
    surgeon_id           - str, surgeon identifier
    status               - str, one of: completed, cancelled, delayed (optional; inferred if absent)
    block_start          - str/time, start of the surgeon's block time (optional)
    block_end            - str/time, end of the surgeon's block time (optional)

Missing optional columns are tolerated; the loader fills reasonable defaults
and documents every inference it makes via the `notes` return value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path
from typing import Union

import pandas as pd

REQUIRED_COLUMNS = [
    "room_id",
    "date",
    "scheduled_start",
    "scheduled_end",
    "procedure_type",
]

OPTIONAL_COLUMNS = [
    "actual_start",
    "actual_end",
    "surgeon_id",
    "status",
    "block_start",
    "block_end",
]

TIME_COLUMNS = [
    "scheduled_start",
    "scheduled_end",
    "actual_start",
    "actual_end",
    "block_start",
    "block_end",
]


@dataclass
class LoadResult:
    df: pd.DataFrame
    notes: list = field(default_factory=list)


def _combine_date_time(d: date_cls, t: str) -> Union[datetime, None]:
    """Combine a date with an HH:MM string into a datetime. Returns None if t is empty/NaN."""
    if pd.isna(t) or str(t).strip() == "":
        return None
    t = str(t).strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
        try:
            parsed = datetime.strptime(t, fmt).time()
            return datetime.combine(d, parsed)
        except ValueError:
            continue
    raise ValueError(f"Could not parse time value: {t!r}")


def load_schedule(path: Union[str, Path]) -> pd.DataFrame:
    """
    Load a procedure-room schedule CSV and return a cleaned DataFrame with
    derived datetime columns and a normalized `status` column.

    Raises
    ------
    ValueError if required columns are missing.
    """
    path = Path(path)
    raw = pd.read_csv(path)
    raw.columns = [c.strip().lower() for c in raw.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(
            f"Missing required column(s): {missing}. "
            f"Required columns are: {REQUIRED_COLUMNS}"
        )

    for col in OPTIONAL_COLUMNS:
        if col not in raw.columns:
            raw[col] = pd.NA

    notes = []

    # Parse date
    raw["date"] = pd.to_datetime(raw["date"]).dt.date

    # Build full datetimes for each time column
    for col in TIME_COLUMNS:
        new_col = f"{col}_dt"
        raw[new_col] = [_combine_date_time(d, t) for d, t in zip(raw["date"], raw[col])]

    # Infer status if not provided
    if raw["status"].isna().all():
        notes.append(
            "No 'status' column provided; inferring from actual_start/actual_end "
            "(missing actual times => cancelled, else completed)."
        )
        raw["status"] = raw.apply(
            lambda r: "cancelled" if pd.isna(r["actual_start_dt"]) else "completed",
            axis=1,
        )
    else:
        raw["status"] = raw["status"].str.strip().str.lower()
        # Fill any remaining blanks using the same inference rule
        blank_mask = raw["status"].isna() | (raw["status"] == "")
        if blank_mask.any():
            notes.append(
                f"{blank_mask.sum()} row(s) had blank status; inferred from actual times."
            )
            raw.loc[blank_mask, "status"] = raw.loc[blank_mask].apply(
                lambda r: "cancelled" if pd.isna(r["actual_start_dt"]) else "completed",
                axis=1,
            )

    # If block times weren't provided, default block = scheduled slot
    if raw["block_start_dt"].isna().all():
        notes.append(
            "No block_start/block_end provided; using scheduled_start/scheduled_end "
            "as the block window for utilization calculations."
        )
        raw["block_start_dt"] = raw["scheduled_start_dt"]
        raw["block_end_dt"] = raw["scheduled_end_dt"]

    # Fill missing surgeon_id
    if raw["surgeon_id"].isna().all():
        notes.append("No surgeon_id provided; all rows assigned 'UNKNOWN'.")
        raw["surgeon_id"] = "UNKNOWN"
    else:
        raw["surgeon_id"] = raw["surgeon_id"].fillna("UNKNOWN")

    raw = raw.sort_values(["room_id", "date", "scheduled_start_dt"]).reset_index(
        drop=True
    )

    result = LoadResult(df=raw, notes=notes)
    for n in result.notes:
        print(f"[loader] {n}")
    return result.df
