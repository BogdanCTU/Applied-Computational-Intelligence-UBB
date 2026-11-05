"""Report generation package: PDF (ReportLab), CSV (UTF-8), sanitization, and history."""

from .canonical_data import (
    CanonicalSQLDataset,
    ChartSpecification,
    ReportConsistencyValidator,
    TransformedChartData,
    extract_and_transform_chart,
    safe_float,
)
from .csv_generator import generate_csv_file
from .date_utils import ReportingPeriod, calculate_previous_calendar_month
from .pdf_generator import generate_pdf_file
from .report_manager import (
    HISTORY_FILENAME,
    ReportHistoryManager,
    ReportMetadata,
    ReportSecurityError,
    ReportValidationError,
    normalize_tabular_data,
    resolve_safe_report_path,
    sanitize_filename_stem,
)

__all__ = [
    "CanonicalSQLDataset",
    "ChartSpecification",
    "HISTORY_FILENAME",
    "ReportConsistencyValidator",
    "ReportHistoryManager",
    "ReportMetadata",
    "ReportSecurityError",
    "ReportValidationError",
    "ReportingPeriod",
    "TransformedChartData",
    "calculate_previous_calendar_month",
    "extract_and_transform_chart",
    "generate_csv_file",
    "generate_pdf_file",
    "normalize_tabular_data",
    "resolve_safe_report_path",
    "safe_float",
    "sanitize_filename_stem",
]
