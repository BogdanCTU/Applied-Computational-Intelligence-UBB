"""Dynamic calendar date and period calculation utilities for reporting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence


_MONTH_NAMES: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


@dataclass(frozen=True)
class ReportingPeriod:
    """Represents a dynamic calendar reporting period using half-open boundaries [start_date, end_date)."""
    start_date: datetime
    end_date: datetime
    start_date_str: str  # YYYY-MM-DD (inclusive)
    end_date_str: str    # YYYY-MM-DD (exclusive next_month_start)
    period_label: str    # e.g. "October 2026"
    year: int
    month: int

    @property
    def year_month(self) -> str:
        """Canonical YYYY-MM string for this calendar month."""
        return f"{self.year:04d}-{self.month:02d}"

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
        """Standard SQLite half-open date comparison filter string."""
        return f">= '{self.start_date_str}' AND < '{self.end_date_str}'"

    def to_dict(self) -> dict[str, Any]:
        """Serialize period details to a JSON-compatible dictionary."""
        return {
            "period_label": self.period_label,
            "year_month": self.year_month,
            "year": self.year,
            "month": self.month,
            "start_date": self.start_date_str,
            "end_date_exclusive": self.end_date_str,
            "sql_filter": self.sql_filter_clause,
        }


def calculate_calendar_month(year: int, month: int) -> ReportingPeriod:
    """Calculate the half-open interval [start_date, next_month_start) for a given year and month."""
    if not (1 <= month <= 12):
        raise ValueError(f"Month must be between 1 and 12, got {month}")

    if month == 12:
        next_year = year + 1
        next_month = 1
    else:
        next_year = year
        next_month = month + 1

    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(next_year, next_month, 1, 0, 0, 0)

    return ReportingPeriod(
        start_date=start_dt,
        end_date=end_dt,
        start_date_str=start_dt.strftime("%Y-%m-%d"),
        end_date_str=end_dt.strftime("%Y-%m-%d"),
        period_label=start_dt.strftime("%B %Y"),
        year=year,
        month=month,
    )


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

    if curr_month == 1:
        prev_year = curr_year - 1
        prev_month = 12
    else:
        prev_year = curr_year
        prev_month = curr_month - 1

    return calculate_calendar_month(prev_year, prev_month)


def parse_year_month_from_date_str(date_str: str | None) -> tuple[int, int] | None:
    """Extract (year, month) from an ISO date/datetime or YYYY-MM string."""
    if not date_str:
        return None
    m = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])\b", str(date_str))
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def resolve_requested_period(
    user_request: str = "",
    title: str = "",
    reference_date: datetime | None = None,
) -> ReportingPeriod | None:
    """Resolve explicit or relative monthly period from user request and report title.

    Always resolves relative expressions ("last month", "previous month") against
    ``reference_date`` (current request time), never against the database's max date.
    Wait-priority:
    1. Explicit month name + year in ``user_request`` (e.g., "October 2026").
    2. Explicit YYYY-MM in ``user_request`` (e.g., "2026-10").
    3. Relative expression in ``user_request`` ("last month", "previous month", "past month").
    4. Explicit month name + year in ``title`` (if ``user_request`` had no period).
    """
    ref = reference_date or datetime.now()
    req_text = (user_request or "").strip()
    title_text = (title or "").strip()

    month_pattern = (
        r"\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|"
        r"july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)"
        r"[\s,\-_]+(20\d{2})\b"
    )

    # 1. Explicit month + year in user_request
    m_req = re.search(month_pattern, req_text, flags=re.IGNORECASE)
    if m_req:
        m_num = _MONTH_NAMES[m_req.group(1).lower()]
        yr = int(m_req.group(2))
        return calculate_calendar_month(yr, m_num)

    # 2. Relative period in user_request ("last month", "previous month", "past month")
    if re.search(r"\b(last|previous|prior|past)\s+month\b", req_text, flags=re.IGNORECASE):
        return calculate_previous_calendar_month(ref)

    if re.search(r"\b(this|current)\s+month\b", req_text, flags=re.IGNORECASE):
        return calculate_calendar_month(ref.year, ref.month)

    # 3. Explicit YYYY-MM in user_request
    ym_req = parse_year_month_from_date_str(req_text)
    if ym_req:
        return calculate_calendar_month(ym_req[0], ym_req[1])

    # 4. Explicit month + year in title
    m_title = re.search(month_pattern, title_text, flags=re.IGNORECASE)
    if m_title:
        m_num = _MONTH_NAMES[m_title.group(1).lower()]
        yr = int(m_title.group(2))
        return calculate_calendar_month(yr, m_num)

    ym_title = parse_year_month_from_date_str(title_text)
    if ym_title:
        return calculate_calendar_month(ym_title[0], ym_title[1])

    return None


@dataclass
class PeriodAvailabilityContext:
    """Explicit separation between requested period, comparison period, available DB range, and SQL data."""

    requested_period: ReportingPeriod | None = None
    comparison_period: ReportingPeriod | None = None
    available_min_date: str | None = None
    available_max_date: str | None = None
    actual_periods_present: list[str] = field(default_factory=list)
    requested_period_has_data: bool = True
    requested_period_record_count: int = 0
    comparison_period_record_count: int = 0
    missing_data_reason: str = "complete"
    data_availability_notes: list[str] = field(default_factory=list)

    @property
    def is_fallback_comparison_active(self) -> bool:
        """Return True when requested period has no data and a historical comparison period is used."""
        return (
            self.requested_period is not None
            and not self.requested_period_has_data
            and self.comparison_period is not None
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize availability context for report specs, metadata, and agent feedback."""
        return {
            "requested_period": self.requested_period.to_dict() if self.requested_period else None,
            "comparison_period": self.comparison_period.to_dict() if self.comparison_period else None,
            "available_min_date": self.available_min_date,
            "available_max_date": self.available_max_date,
            "actual_periods_present": list(self.actual_periods_present),
            "requested_period_has_data": self.requested_period_has_data,
            "requested_period_record_count": self.requested_period_record_count,
            "comparison_period_record_count": self.comparison_period_record_count,
            "missing_data_reason": self.missing_data_reason,
            "is_fallback_comparison_active": self.is_fallback_comparison_active,
            "data_availability_notes": list(self.data_availability_notes),
        }

