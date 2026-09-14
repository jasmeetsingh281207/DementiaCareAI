"""
Cognitive tracker compatibility layer.

All records are stored through dashboard.reports
and database.py.
"""


from dashboard.reports import (
    record_performance,
    get_performance_history,
    get_performance_summary
)


__all__ = [
    "record_performance",
    "get_performance_history",
    "get_performance_summary"
]