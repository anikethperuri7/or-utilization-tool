"""
generate_sample_data.py
------------------------
Generates a realistic, fully SYNTHETIC procedure-room schedule dataset for
demoing and testing the OR Utilization Tool. No real patient, surgeon, or
hospital data is used anywhere in this repository.

Run:
    python scripts/generate_sample_data.py --out data/sample_schedule.csv --days 60 --rooms 5
"""

from __future__ import annotations

import argparse
import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

PROCEDURES = [
    ("Total Knee Arthroplasty", 120),
    ("Total Hip Arthroplasty", 135),
    ("Laparoscopic Cholecystectomy", 60),
    ("Appendectomy", 45),
    ("Cataract Surgery", 30),
    ("Rotator Cuff Repair", 90),
    ("Spinal Fusion", 180),
    ("Carpal Tunnel Release", 25),
    ("Hernia Repair", 55),
    ("Tonsillectomy", 35),
    ("ACL Reconstruction", 100),
    ("Cesarean Section", 50),
]

SURGEONS = [f"SUR-{i:03d}" for i in range(1, 13)]
ROOM_START = "07:00"
ROOM_END = "17:00"


def _time_to_minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _minutes_to_time(m: int) -> str:
    m = int(m) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def generate(days: int, rooms: int, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    room_ids = [f"OR-{i}" for i in range(1, rooms + 1)]
    start_date = date(2025, 1, 6)  # a Monday

    rows = []
    day_count = 0
    d = start_date
    while day_count < days:
        if d.weekday() >= 5:  # skip weekends
            d += timedelta(days=1)
            continue

        for room in room_ids:
            # Each room has a block from 07:00 to 17:00 (600 min), assigned to
            # a "home" surgeon for the day with occasional add-on cases.
            block_start_min = _time_to_minutes(ROOM_START)
            block_end_min = _time_to_minutes(ROOM_END)
            cursor = block_start_min

            home_surgeon = rng.choice(SURGEONS)
            n_cases_planned = rng.choice([3, 3, 4, 4, 4, 5, 5, 6])

            for case_idx in range(n_cases_planned):
                if cursor >= block_end_min - 20:
                    break

                proc_name, base_duration = rng.choice(PROCEDURES)
                sched_duration = max(20, int(np_rng.normal(base_duration, base_duration * 0.1)))

                sched_start = cursor
                sched_end = sched_start + sched_duration
                if sched_end > block_end_min:
                    sched_end = block_end_min
                    sched_duration = sched_end - sched_start
                    if sched_duration < 15:
                        break

                # ---- Simulate realistic operational noise ----
                is_cancelled = rng.random() < 0.06  # ~6% cancellation rate

                # First case of day more prone to delay; later cases inherit
                # cascading delay from prior overruns (handled via cursor drift).
                base_delay = np_rng.normal(8 if case_idx == 0 else 4, 6)
                start_delay = max(0, base_delay) if not is_cancelled else np.nan

                # Actual duration: noisy around scheduled, with a long right tail
                # (cases that run over) more likely later in the day.
                overrun_bias = 1.0 + (0.03 * case_idx)
                actual_duration = max(
                    10,
                    np_rng.normal(sched_duration * overrun_bias, sched_duration * 0.18),
                )

                actual_start_min = sched_start + start_delay if not is_cancelled else None
                actual_end_min = (
                    actual_start_min + actual_duration if not is_cancelled else None
                )

                surgeon = home_surgeon if rng.random() > 0.15 else rng.choice(SURGEONS)

                rows.append(
                    {
                        "room_id": room,
                        "date": d.isoformat(),
                        "scheduled_start": _minutes_to_time(sched_start),
                        "scheduled_end": _minutes_to_time(sched_end),
                        "actual_start": _minutes_to_time(actual_start_min) if actual_start_min is not None else "",
                        "actual_end": _minutes_to_time(actual_end_min) if actual_end_min is not None else "",
                        "procedure_type": proc_name,
                        "surgeon_id": surgeon,
                        "status": "cancelled" if is_cancelled else "completed",
                        "block_start": ROOM_START,
                        "block_end": ROOM_END,
                    }
                )

                # Advance cursor: use actual end (or scheduled if cancelled) plus
                # a realistic turnaround gap so subsequent cases show cascading delay.
                if is_cancelled:
                    cursor = sched_end + rng.randint(5, 15)
                else:
                    turnaround = max(10, int(np_rng.normal(22, 8)))
                    cursor = int(actual_end_min) + turnaround

        day_count += 1
        d += timedelta(days=1)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/sample_schedule.csv")
    parser.add_argument("--days", type=int, default=60, help="Number of weekdays to simulate.")
    parser.add_argument("--rooms", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = generate(args.days, args.rooms, args.seed)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows across {args.rooms} rooms x {args.days} weekdays to {args.out}")


if __name__ == "__main__":
    main()
