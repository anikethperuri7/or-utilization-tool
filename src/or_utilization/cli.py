"""
cli.py
------
Command-line interface for the OR Utilization Tool.

Usage
-----
    or-util analyze --input data/sample_schedule.csv --output-dir reports/latest

    or-util simulate --input data/sample_schedule.csv --output-dir reports/latest \\
        --turnaround-reduction 10 --start-delay-reduction-pct 30 --overrun-reduction-pct 25
"""

from __future__ import annotations

import argparse
import json
import sys

from .loader import load_schedule
from .metrics import compute_metrics
from .report import generate_markdown_report
from .simulate import simulate_schedule_optimization


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="or-util",
        description="Analyze OR / procedure room scheduling data for utilization, "
        "delays, overruns, cancellations, and turnaround times.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="Compute metrics and generate a report.")
    analyze.add_argument("--input", required=True, help="Path to schedule CSV.")
    analyze.add_argument(
        "--output-dir",
        default="reports/latest",
        help="Directory for the report + charts.",
    )
    analyze.add_argument(
        "--json-summary",
        action="store_true",
        help="Print overall summary as JSON to stdout.",
    )

    simulate = sub.add_parser(
        "simulate", help="Run a schedule-optimization simulation and generate a report."
    )
    simulate.add_argument("--input", required=True, help="Path to schedule CSV.")
    simulate.add_argument(
        "--output-dir",
        default="reports/latest",
        help="Directory for the report + charts.",
    )
    simulate.add_argument(
        "--turnaround-reduction",
        type=float,
        default=10.0,
        help="Minutes shaved off each turnaround gap. Default 10.",
    )
    simulate.add_argument(
        "--start-delay-reduction-pct",
        type=float,
        default=25.0,
        help="Percent reduction applied to average start delay. Default 25.",
    )
    simulate.add_argument(
        "--overrun-reduction-pct",
        type=float,
        default=25.0,
        help="Percent reduction applied to total overrun minutes. Default 25.",
    )
    simulate.add_argument(
        "--avg-case-length-min",
        type=float,
        default=None,
        help="Override the average case length used to convert minutes to case counts.",
    )
    simulate.add_argument("--scenario-name", default="custom_scenario")
    simulate.add_argument("--json-summary", action="store_true")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    df = load_schedule(args.input)
    metrics = compute_metrics(df)

    if args.command == "analyze":
        report_path = generate_markdown_report(metrics, args.output_dir)
        print(f"Report written to: {report_path}")
        if args.json_summary:
            print(json.dumps(metrics.overall, indent=2, default=str))

    elif args.command == "simulate":
        sim = simulate_schedule_optimization(
            metrics.daily_room_summary,
            turnaround_reduction_min=args.turnaround_reduction,
            start_delay_reduction_pct=args.start_delay_reduction_pct,
            overrun_reduction_pct=args.overrun_reduction_pct,
            avg_case_length_min=args.avg_case_length_min,
            scenario_name=args.scenario_name,
        )
        report_path = generate_markdown_report(metrics, args.output_dir, simulation=sim)
        print(f"Report written to: {report_path}")
        if args.json_summary:
            print(json.dumps(sim.summary, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
