"""
OR Utilization Tool
====================

A data analysis toolkit for operating room / procedure room scheduling data.
Computes room utilization, turnaround times, delays, overruns, and
cancellation patterns, and simulates schedule-optimization scenarios to
estimate how many additional procedures could fit in existing block time.
"""

from .loader import load_schedule
from .metrics import UtilizationMetrics, compute_metrics
from .simulate import SimulationResult, simulate_schedule_optimization

__version__ = "0.1.0"

__all__ = [
    "UtilizationMetrics",
    "compute_metrics",
    "SimulationResult",
    "simulate_schedule_optimization",
    "load_schedule",
]
