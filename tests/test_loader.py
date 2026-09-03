import pandas as pd
import pytest

from or_utilization.loader import load_schedule


def test_load_schedule_basic_shape(tiny_schedule_df):
    assert len(tiny_schedule_df) == 3
    assert set(tiny_schedule_df["status"]) == {"completed", "cancelled"}


def test_load_schedule_parses_datetimes(tiny_schedule_df):
    row = tiny_schedule_df.iloc[0]
    assert row["scheduled_start_dt"] == pd.Timestamp("2025-01-06 07:00:00")
    assert row["actual_end_dt"] == pd.Timestamp("2025-01-06 08:20:00")


def test_load_schedule_cancelled_case_has_null_actuals(tiny_schedule_df):
    cancelled = tiny_schedule_df[tiny_schedule_df["status"] == "cancelled"].iloc[0]
    assert pd.isna(cancelled["actual_start_dt"])
    assert pd.isna(cancelled["actual_end_dt"])


def test_load_schedule_missing_required_column_raises(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    pd.DataFrame({"room_id": ["OR-1"], "date": ["2025-01-06"]}).to_csv(
        bad_csv, index=False
    )
    with pytest.raises(ValueError, match="Missing required column"):
        load_schedule(bad_csv)


def test_load_schedule_infers_status_when_absent(tmp_path):
    df_in = pd.DataFrame(
        [
            {
                "room_id": "OR-1",
                "date": "2025-01-06",
                "scheduled_start": "07:00",
                "scheduled_end": "08:00",
                "actual_start": "07:00",
                "actual_end": "08:05",
                "procedure_type": "Proc",
            },
            {
                "room_id": "OR-1",
                "date": "2025-01-06",
                "scheduled_start": "09:00",
                "scheduled_end": "10:00",
                "actual_start": "",
                "actual_end": "",
                "procedure_type": "Proc",
            },
        ]
    )
    path = tmp_path / "no_status.csv"
    df_in.to_csv(path, index=False)
    result = load_schedule(path)
    assert result.iloc[0]["status"] == "completed"
    assert result.iloc[1]["status"] == "cancelled"


def test_load_schedule_defaults_block_to_scheduled_when_absent(tmp_path):
    df_in = pd.DataFrame(
        [
            {
                "room_id": "OR-1",
                "date": "2025-01-06",
                "scheduled_start": "07:00",
                "scheduled_end": "08:00",
                "actual_start": "07:00",
                "actual_end": "08:00",
                "procedure_type": "Proc",
            }
        ]
    )
    path = tmp_path / "no_block.csv"
    df_in.to_csv(path, index=False)
    result = load_schedule(path)
    assert result.iloc[0]["block_start_dt"] == result.iloc[0]["scheduled_start_dt"]
    assert result.iloc[0]["block_end_dt"] == result.iloc[0]["scheduled_end_dt"]
