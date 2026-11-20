"""AST-based SQL parser, schema grounding resolver, and structured target serializer."""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import sqlglot
from sqlglot import exp
from app.core.logging import get_logger
from app.database.schema_manager import DatabaseSchema

logger = get_logger(__name__)


@dataclass
class SchemaAnnotationResult:
    """Detailed result of schema-grounding resolution on a SQL query."""

    example_id: str
    db_id: str
    status: str  # 'success', 'partial', 'rejected'
    tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    foreign_key_validated_count: int = 0
    rejection_reason: Optional[str] = None
    unresolved_aliases: List[str] = field(default_factory=list)
    unresolved_columns: List[str] = field(default_factory=list)
    structured_target: str = ""
    reference_sql: str = ""


class ASTSchemaAnnotator:
    """Parses SQL queries into ASTs, resolves schema entities, and generates structured annotations."""

    def __init__(self):
        pass

    def annotate(
        self,
        query: str,
        db_schema: DatabaseSchema,
        example_id: str = "example_0",
    ) -> SchemaAnnotationResult:
        """Parses a reference SQL query and resolves relevant tables, columns, and relationships."""
        ref_sql = query.strip()
        if not ref_sql:
            return SchemaAnnotationResult(
                example_id=example_id,
                db_id=db_schema.db_id,
                status="rejected",
                rejection_reason="Empty SQL query",
                reference_sql=ref_sql,
            )

        # 1. Parse into AST via sqlglot SQLite dialect
        try:
            parsed = sqlglot.parse_one(ref_sql, read="sqlite")
        except Exception as e:
            return SchemaAnnotationResult(
                example_id=example_id,
                db_id=db_schema.db_id,
                status="rejected",
                rejection_reason=f"AST parse failure: {str(e)}",
                reference_sql=ref_sql,
            )

        # 2. Build Schema Lookup Index (Case-Insensitive)
        schema_tables: Dict[str, str] = {t.lower(): t for t in db_schema.tables.keys()}
        schema_cols: Dict[str, Dict[str, str]] = {}
        declared_fks: Set[Tuple[str, str]] = set()

        for t_orig, t_obj in db_schema.tables.items():
            schema_cols[t_orig.lower()] = {c.name.lower(): c.name for c in t_obj.columns}
            for fk in t_obj.foreign_keys:
                pair = tuple(sorted([f"{t_orig.lower()}.{fk.column.lower()}", f"{fk.ref_table.lower()}.{fk.ref_column.lower()}"]))
                declared_fks.add(pair)

        # 3. Identify CTEs
        cte_names: Set[str] = set()
        for cte in parsed.find_all(exp.CTE):
            if cte.alias:
                cte_names.add(cte.alias.lower())

        # 4. Resolve Tables and Table Aliases
        alias_to_table: Dict[str, str] = {}
        referenced_tables: Set[str] = set()
        unresolved_aliases: List[str] = []

        for t in parsed.find_all(exp.Table):
            t_raw = t.name
            if not t_raw or t_raw.lower() in cte_names:
                continue

            canonical_t = schema_tables.get(t_raw.lower())
            if canonical_t:
                referenced_tables.add(canonical_t)
                alias_to_table[canonical_t.lower()] = canonical_t
                if t.alias:
                    alias_to_table[t.alias.lower()] = canonical_t
            else:
                unresolved_aliases.append(t_raw)

        if not referenced_tables:
            return SchemaAnnotationResult(
                example_id=example_id,
                db_id=db_schema.db_id,
                status="rejected",
                rejection_reason="No schema tables identified in query",
                reference_sql=ref_sql,
            )

        # 5. Resolve Columns
        resolved_cols: Set[str] = set()
        unresolved_columns: List[str] = []

        for c in parsed.find_all(exp.Column):
            col_name = c.name
            if not col_name or col_name == "*":
                continue

            # Check if column is qualified with a table/alias
            if c.table:
                t_lookup = alias_to_table.get(c.table.lower())
                if t_lookup:
                    col_canonical = schema_cols.get(t_lookup.lower(), {}).get(col_name.lower())
                    if col_canonical:
                        resolved_cols.add(f"{t_lookup}.{col_canonical}")
                    else:
                        unresolved_columns.append(f"{c.table}.{col_name}")
                elif c.table.lower() not in cte_names:
                    unresolved_columns.append(f"{c.table}.{col_name}")
            else:
                # Unqualified column: search candidate tables
                candidates = [
                    t for t in referenced_tables
                    if col_name.lower() in schema_cols.get(t.lower(), {})
                ]
                if len(candidates) == 1:
                    t_cand = candidates[0]
                    col_canonical = schema_cols[t_cand.lower()][col_name.lower()]
                    resolved_cols.add(f"{t_cand}.{col_canonical}")
                elif len(candidates) > 1:
                    # Ambiguous reference across multiple tables in the query
                    unresolved_columns.append(f"AMBIGUOUS:{col_name}")
                else:
                    # Check if column is an expression alias (e.g. SELECT count(*) as cnt ... ORDER BY cnt)
                    # We do not count expression aliases as base schema columns
                    pass

        # 6. Resolve Join Relationships
        resolved_rels: Set[str] = set()
        fk_validated = 0

        # Collect equality pairs from JOIN ON and WHERE clauses
        for eq in parsed.find_all(exp.EQ):
            if isinstance(eq.this, exp.Column) and isinstance(eq.expression, exp.Column):
                c1, c2 = eq.this, eq.expression
                t1 = alias_to_table.get(c1.table.lower()) if c1.table else None
                t2 = alias_to_table.get(c2.table.lower()) if c2.table else None

                if t1 and t2 and t1.lower() != t2.lower():
                    col1_name = schema_cols.get(t1.lower(), {}).get(c1.name.lower(), c1.name)
                    col2_name = schema_cols.get(t2.lower(), {}).get(c2.name.lower(), c2.name)

                    c1_str = f"{t1}.{col1_name}"
                    c2_str = f"{t2}.{col2_name}"
                    pair = sorted([c1_str, c2_str])
                    rel_str = f"{pair[0]} = {pair[1]}"
                    resolved_rels.add(rel_str)

                    # Check against declared foreign keys
                    fk_pair = tuple(sorted([f"{t1.lower()}.{col1_name.lower()}", f"{t2.lower()}.{col2_name.lower()}"]))
                    if fk_pair in declared_fks:
                        fk_validated += 1

        sorted_tables = sorted(list(referenced_tables))
        sorted_cols = sorted(list(resolved_cols))
        sorted_rels = sorted(list(resolved_rels))

        # 7. Determine Annotation Quality Status
        status = "success"
        rejection_reason = None

        if unresolved_aliases:
            status = "partial"
            rejection_reason = f"Unresolved table aliases: {unresolved_aliases}"
        elif unresolved_columns:
            status = "partial"
            rejection_reason = f"Unresolved columns: {unresolved_columns}"

        # 8. Format Structured Target String
        structured_target = self.serialize_target(
            tables=sorted_tables,
            columns=sorted_cols,
            relationships=sorted_rels,
            sql=ref_sql,
        )

        return SchemaAnnotationResult(
            example_id=example_id,
            db_id=db_schema.db_id,
            status=status,
            tables=sorted_tables,
            columns=sorted_cols,
            relationships=sorted_rels,
            foreign_key_validated_count=fk_validated,
            rejection_reason=rejection_reason,
            unresolved_aliases=unresolved_aliases,
            unresolved_columns=unresolved_columns,
            structured_target=structured_target,
            reference_sql=ref_sql,
        )

    @staticmethod
    def serialize_target(
        tables: List[str],
        columns: List[str],
        relationships: List[str],
        sql: str,
    ) -> str:
        """Serializes schema elements and reference SQL into canonical structured format."""
        rel_str = ", ".join(relationships) if relationships else "NONE"
        tables_str = ", ".join(tables) if tables else "NONE"
        cols_str = ", ".join(columns) if columns else "NONE"

        return (
            "<SCHEMA_SELECTION>\n"
            f"TABLES: {tables_str}\n"
            f"COLUMNS: {cols_str}\n"
            f"RELATIONSHIPS: {rel_str}\n"
            "</SCHEMA_SELECTION>\n\n"
            "<SQL>\n"
            f"{sql.strip()}\n"
            "</SQL>"
        )

    @staticmethod
    def parse_structured_output(text: str) -> Tuple[List[str], List[str], List[str], str]:
        """Safely parses structured model response into (tables, columns, relationships, sql)."""
        tables: List[str] = []
        columns: List[str] = []
        relationships: List[str] = []
        sql_query = ""

        if not text:
            return tables, columns, relationships, sql_query

        # Extract <SCHEMA_SELECTION>...</SCHEMA_SELECTION>
        schema_match = re.search(r"<SCHEMA_SELECTION>([\s\S]*?)</SCHEMA_SELECTION>", text, re.IGNORECASE)
        if schema_match:
            schema_block = schema_match.group(1)

            t_match = re.search(r"TABLES:\s*([^\n\r]+)", schema_block, re.IGNORECASE)
            if t_match and t_match.group(1).strip().upper() != "NONE":
                tables = [t.strip() for t in t_match.group(1).split(",") if t.strip()]

            c_match = re.search(r"COLUMNS:\s*([^\n\r]+)", schema_block, re.IGNORECASE)
            if c_match and c_match.group(1).strip().upper() != "NONE":
                columns = [c.strip() for c in c_match.group(1).split(",") if c.strip()]

            r_match = re.search(r"RELATIONSHIPS:\s*([^\n\r]+)", schema_block, re.IGNORECASE)
            if r_match and r_match.group(1).strip().upper() != "NONE":
                relationships = [r.strip() for r in r_match.group(1).split(",") if r.strip()]

        # Extract <SQL>...</SQL>
        sql_match = re.search(r"<SQL>([\s\S]*?)</SQL>", text, re.IGNORECASE)
        if sql_match:
            sql_query = sql_match.group(1).strip()
        else:
            # Fallback: check markdown ```sql block or SELECT
            md_match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
            if md_match:
                sql_query = md_match.group(1).strip()
            else:
                sel_match = re.search(r"\b(SELECT\b[\s\S]*?)(?:;|\Z)", text, re.IGNORECASE)
                if sel_match:
                    sql_query = sel_match.group(1).strip()

        return tables, columns, relationships, sql_query
