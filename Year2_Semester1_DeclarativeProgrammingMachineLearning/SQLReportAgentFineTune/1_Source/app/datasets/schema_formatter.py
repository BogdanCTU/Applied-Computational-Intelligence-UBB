"""Formats database schemas into concise prompts for LLM training and inference."""

from typing import Dict, List, Optional
from app.database.schema_manager import DatabaseSchema


class SchemaFormatter:
    """Formats schemas into consistent Text-to-SQL prompt representations."""

    @staticmethod
    def format_for_prompt(schema: DatabaseSchema, style: str = "concise") -> str:
        """Formats a DatabaseSchema into a prompt-ready string."""
        if style == "ddl":
            return schema.to_ddl()
        return schema.to_prompt_schema()

    @staticmethod
    def format_raw_schema(
        tables: Dict[str, List[str]],
        foreign_keys: Optional[List[str]] = None,
        db_id: str = "default_db",
    ) -> str:
        """Formats a dictionary of table -> columns into schema text."""
        lines = [f"Database Schema [{db_id}]:"]
        for table, cols in tables.items():
            lines.append(f"- Table `{table}`: " + ", ".join(cols))
        if foreign_keys:
            lines.append("Relationships:")
            for fk in foreign_keys:
                lines.append(f"  * {fk}")
        return "\n".join(lines)
