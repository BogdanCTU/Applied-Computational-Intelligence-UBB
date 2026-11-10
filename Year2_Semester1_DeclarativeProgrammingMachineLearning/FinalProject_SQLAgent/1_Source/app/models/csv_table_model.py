"""High-performance tabular data model for displaying CSV reports in QTableView."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

log = logging.getLogger(__name__)

DEFAULT_MAX_PREVIEW_ROWS = 5000


class CsvTableModel(QAbstractTableModel):
    """Tabular data model for CSV file previewing with memory safety caps."""

    def __init__(
        self,
        headers: list[str] | None = None,
        rows: list[list[Any]] | None = None,
        *,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._headers: list[str] = list(headers or [])
        self._rows: list[list[str]] = [
            [str(cell) if cell is not None else "" for cell in row]
            for row in (rows or [])
        ]
        self._total_file_rows: int = len(self._rows)
        self._is_truncated: bool = False
        self._file_path: Path | None = None

    @property
    def headers(self) -> list[str]:
        return list(self._headers)

    @property
    def total_file_rows(self) -> int:
        return self._total_file_rows

    @property
    def is_truncated(self) -> bool:
        return self._is_truncated

    @property
    def file_path(self) -> Path | None:
        return self._file_path

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row, col = index.row(), index.column()
        if not (0 <= row < len(self._rows) and 0 <= col < len(self._headers)):
            return None

        val = self._rows[row][col] if col < len(self._rows[row]) else ""

        if role == Qt.ItemDataRole.DisplayRole:
            return val if val != "" else "—"

        if role == Qt.ItemDataRole.TextAlignmentRole:
            # Numeric values look better right-aligned
            if val and val.replace(".", "", 1).replace("-", "", 1).isdigit():
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        if role == Qt.ItemDataRole.ToolTipRole:
            return f"Column: {self._headers[col]}\nValue: {val}"

        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if 0 <= section < len(self._headers):
                    return self._headers[section]
                return f"Col {section + 1}"
            return str(section + 1)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter

        return None

    def load_file(
        self,
        file_path: str | Path,
        *,
        max_rows: int = DEFAULT_MAX_PREVIEW_ROWS,
    ) -> bool:
        """Load and parse CSV data from ``file_path`` safely with a row cap."""
        p = Path(file_path).resolve()
        if not p.is_file():
            log.warning("CSV file does not exist: %s", p)
            return False

        headers: list[str] = []
        rows: list[list[str]] = []
        total_count = 0
        is_trunc = False

        # Try UTF-8 first, fallback to Latin-1
        encoding = "utf-8"
        try:
            with p.open("r", encoding="utf-8", errors="replace", newline="") as fh:
                reader = csv.reader(fh)
                try:
                    headers = next(reader)
                except StopIteration:
                    headers = []

                for row in reader:
                    total_count += 1
                    if len(rows) < max_rows:
                        rows.append(row)
                    else:
                        is_trunc = True
        except Exception as exc:  # noqa: BLE001
            log.error("Failed to read CSV %s: %s", p, exc)
            return False

        self.beginResetModel()
        self._file_path = p
        self._headers = headers
        self._rows = rows
        self._total_file_rows = total_count
        self._is_truncated = is_trunc
        self.endResetModel()
        return True

    def clear(self) -> None:
        """Clear all data from the model."""
        self.beginResetModel()
        self._headers.clear()
        self._rows.clear()
        self._total_file_rows = 0
        self._is_truncated = False
        self._file_path = None
        self.endResetModel()

