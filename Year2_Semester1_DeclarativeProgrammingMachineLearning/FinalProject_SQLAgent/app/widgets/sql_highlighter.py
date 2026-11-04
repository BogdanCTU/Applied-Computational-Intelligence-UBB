"""SQL syntax highlighter for PySide6 text components."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument


class SqlSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for SQL queries in QPlainTextEdit and QTextEdit."""

    def __init__(self, parent: QTextDocument | None = None) -> None:
        super().__init__(parent)
        self._highlighting_rules: list[tuple[re.Pattern[str], QTextCharFormat]] = []

        # 1. Keywords format (Vibrant Cyan / Blue)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#60a5fa"))
        keyword_format.setFontWeight(QFont.Weight.Bold)

        keywords = [
            r"\bSELECT\b",
            r"\bFROM\b",
            r"\bWHERE\b",
            r"\bGROUP\s+BY\b",
            r"\bORDER\s+BY\b",
            r"\bHAVING\b",
            r"\bLIMIT\b",
            r"\bOFFSET\b",
            r"\bJOIN\b",
            r"\bINNER\s+JOIN\b",
            r"\bLEFT\s+JOIN\b",
            r"\bLEFT\s+OUTER\s+JOIN\b",
            r"\bCROSS\s+JOIN\b",
            r"\bON\b",
            r"\bAS\b",
            r"\bAND\b",
            r"\bOR\b",
            r"\bNOT\b",
            r"\bIN\b",
            r"\bIS\b",
            r"\bNULL\b",
            r"\bLIKE\b",
            r"\bBETWEEN\b",
            r"\bEXISTS\b",
            r"\bCASE\b",
            r"\bWHEN\b",
            r"\bTHEN\b",
            r"\bELSE\b",
            r"\bEND\b",
            r"\bWITH\b",
            r"\bRECURSIVE\b",
            r"\bUNION\b",
            r"\bUNION\s+ALL\b",
            r"\bDISTINCT\b",
            r"\bASC\b",
            r"\bDESC\b",
            r"\bCAST\b",
        ]
        for pattern in keywords:
            self._highlighting_rules.append(
                (re.compile(pattern, re.IGNORECASE), keyword_format)
            )

        # 2. Built-in SQL Functions (Warm Amber / Gold)
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#fbbf24"))

        functions = [
            r"\bCOUNT\b",
            r"\bSUM\b",
            r"\bAVG\b",
            r"\bMIN\b",
            r"\bMAX\b",
            r"\bTOTAL\b",
            r"\bROUND\b",
            r"\bCOALESCE\b",
            r"\bSTRFTIME\b",
            r"\bDATE\b",
            r"\bDATETIME\b",
            r"\bTIME\b",
            r"\bJULIANDAY\b",
            r"\bUPPER\b",
            r"\bLOWER\b",
            r"\bLENGTH\b",
            r"\bSUBSTR\b",
            r"\bTRIM\b",
            r"\bREPLACE\b",
            r"\bIFNULL\b",
            r"\bNULLIF\b",
            r"\bROW_NUMBER\b",
            r"\bRANK\b",
            r"\bDENSE_RANK\b",
            r"\bOVER\b",
            r"\bPARTITION\s+BY\b",
        ]
        for pattern in functions:
            self._highlighting_rules.append(
                (re.compile(pattern, re.IGNORECASE), function_format)
            )

        # 3. Numeric Literals (Purple / Violet)
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#c084fc"))
        self._highlighting_rules.append(
            (re.compile(r"\b\d+(?:\.\d+)?\b"), number_format)
        )

        # 4. String Literals (Emerald Green)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#34d399"))
        self._highlighting_rules.append(
            (re.compile(r"'[^']*'"), string_format)
        )

        # 5. Comments (Muted Slate / Gray)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#94a3b8"))
        self.comment_format.setFontItalic(True)
        self._highlighting_rules.append(
            (re.compile(r"--[^\n]*"), self.comment_format)
        )

        # Multi-line comment regex
        self._comment_start = re.compile(r"/\*")
        self._comment_end = re.compile(r"\*/")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, fmt in self._highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)

        # Multi-line comment handling
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            match = self._comment_start.search(text)
            start_index = match.start() if match else -1
        else:
            start_index = 0

        while start_index >= 0:
            match_end = self._comment_end.search(text, start_index)
            if match_end:
                end_index = match_end.end()
                comment_length = end_index - start_index
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index

            self.setFormat(start_index, comment_length, self.comment_format)
            match_next = self._comment_start.search(text, start_index + comment_length)
            start_index = match_next.start() if match_next else -1

