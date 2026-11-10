"""Report generation package: PDF (ReportLab), CSV (UTF-8), sanitization, and history."""

from .canonical_data import (
    AUTHORITATIVE_METRIC_DEFINITIONS,
    CanonicalSQLDataset,
    ChartSpecification,
    ReportConsistencyValidator,
    TransformedChartData,
    extract_and_transform_chart,
    safe_float,
    validate_tabular_rows_structure,
)
from .csv_generator import generate_csv_file
from .dataset_registry import CuratedDataset, ReportDatasetRegistry
from .date_utils import (
    PeriodAvailabilityContext,
    ReportingPeriod,
    calculate_calendar_month,
    calculate_previous_calendar_month,
    resolve_requested_period,
)
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
from .report_validator import ReportDataValidator, ReportValidationReport

__all__ = [
    "AUTHORITATIVE_METRIC_DEFINITIONS",
    "CanonicalSQLDataset",
    "ChartSpecification",
    "CuratedDataset",
    "HISTORY_FILENAME",
    "PeriodAvailabilityContext",
    "ReportConsistencyValidator",
    "ReportDataValidator",
    "ReportDatasetRegistry",
    "ReportHistoryManager",
    "ReportMetadata",
    "ReportSecurityError",
    "ReportValidationError",
    "ReportValidationReport",
    "ReportingPeriod",
    "TransformedChartData",
    "calculate_calendar_month",
    "calculate_previous_calendar_month",
    "extract_and_transform_chart",
    "generate_csv_file",
    "generate_pdf_file",
    "normalize_tabular_data",
    "resolve_requested_period",
    "resolve_safe_report_path",
    "safe_float",
    "sanitize_filename_stem",
    "validate_tabular_rows_structure",
]
