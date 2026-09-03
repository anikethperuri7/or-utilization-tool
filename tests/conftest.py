"""Shared pytest fixtures: a small, hand-crafted schedule CSV with known
ground-truth values so metric calculations can be checked exactly."""

import pandas as pd
import pytest
from pathlib import Path

from or_utilization.loader import load_schedule


@pytest.fixture
def tiny_schedule_csv(tmp_path) -> Path:
    """
    A hand-crafted 1-room, 1-day schedule with known values:

    Case 1: scheduled 07:00-08:00 (60 min), actual 07:10-08:20 (70 min)
             -> start_delay = 10 min, overrun = 20 min
    Case 2: scheduled 08:30-09:00 (30 min), CANCELLED
    Case 3: scheduled 09:15-10:15 (60 min), actual 09:30-10:00 (30 min)
             -> start_delay = 15 min, early finish (overrun = -15, clipped to 0)

    Block: 07:00-12:00 (300 min)
    Occupied: 70 + 30 = 100 min (only completed cases count)
    Utilization: 100/300 = 33.33%
    Turnaround (case1 end 08:20 -> case3 start 09:30) = 70 min
    """
    rows = [
        {
            "room_id": "OR-TEST",
            "date": "2025-01-06",
            "scheduled_start": "07:00",
            "scheduled_end": "08:00",
            "actual_start": "07:10",
            "actual_end": "08:20",
            "procedure_type": "Test Procedure A",
            "surgeon_id": "SUR-TEST-1",
            "status": "completed",
            "block_start": "07:00",
            "block_end": "12:00",
        },
        {
            "room_id": "OR-TEST",
            "date": "2025-01-06",
            "scheduled_start": "08:30",
            "scheduled_end": "09:00",
            "actual_start": "",
            "actual_end": "",
            "procedure_type": "Test Procedure B",
            "surgeon_id": "SUR-TEST-1",
            "status": "cancelled",
            "block_start": "07:00",
            "block_end": "12:00",
        },
        {
            "room_id": "OR-TEST",
            "date": "2025-01-06",
            "scheduled_start": "09:15",
            "scheduled_end": "10:15",
            "actual_start": "09:30",
            "actual_end": "10:00",
            "procedure_type": "Test Procedure C",
            "surgeon_id": "SUR-TEST-2",
            "status": "completed",
            "block_start": "07:00",
            "block_end": "12:00",
        },
    ]
    df = pd.DataFrame(rows)
    path = tmp_path / "tiny_schedule.csv"
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def tiny_schedule_df(tiny_schedule_csv) -> pd.DataFrame:
    return load_schedule(tiny_schedule_csv)
