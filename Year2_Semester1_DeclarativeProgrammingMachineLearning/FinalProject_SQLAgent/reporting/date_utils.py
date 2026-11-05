"""Dynamic calendar date and period calculation utilities for reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class ReportingPeriod:
    """Represents a dynamic calendar reporting period."""
    start_date: datetime
    end_date: datetime
    start_date_str: str  # YYYY-MM-DD
    end_date_str: str    # YYYY-MM-DD
    period_label: str    # e.g. "October 2026"
    year: int
    month: int

    @property
    def end_date_exclusive(self) -> str:
        """Alias for end_date_str representing the exclusive boundary."""
        return self.end_date_str

    @property
    def start_date_inclusive(self) -> str:
        """Alias for start_date_str representing the inclusive boundary."""
        return self.start_date_str

    @property
    def sql_filter_clause(self) -> str:
        """Standard SQLite date comparison filter string."""
        return f">= '{self.start_date_str}' AND < '{self.end_date_str}'"


def calculate_previous_calendar_month(
    reference_date: datetime | None = None,
) -> ReportingPeriod:
    """Calculate the previous complete calendar month dynamically relative to ``reference_date``.

    - Start: first day of previous month, inclusive (00:00:00).
    - End: first day of current month, exclusive (00:00:00).
    """
    ref = reference_date or datetime.now()
    curr_year = ref.year
    curr_month = ref.month

    # Calculate previous calendar month
    if curr_month == 1:
        prev_year = curr_year - 1
        prev_month = 12
    else:
        prev_year = curr_year
        prev_month = curr_month - 1

    start_dt = datetime(prev_year, prev_month, 1, 0, 0, 0)
    end_dt = datetime(curr_year, curr_month, 1, 0, 0, 0)

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    label = start_dt.strftime("%B %Y")

    return ReportingPeriod(
        start_date=start_dt,
        end_date=end_dt,
        start_date_str=start_str,
        end_date_str=end_str,
        period_label=label,
        year=prev_year,
        month=prev_month,
    )
