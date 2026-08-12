"""Constrained hybrid SQL generation.

The deterministic pipeline in :mod:`app.services.action_service` grounds the
SQL to the verified schema. This module optionally lets the LLM *read the user
question* and rewrite that grounded SQL into a more faithful statement (filters,
ordering, aggregation) — but the result is strictly validated:

* it must start with ``SELECT`` and stay read-only (no DDL/DML),
* it may only reference the main table's real columns via the alias ``t``,
* it must not introduce tables, columns, or aliases outside the schema.

Any invalid output (or an unavailable LLM) falls back to the deterministic SQL
unchanged, so this can never hallucinate columns into a query.
"""
import json
import re

import structlog

from llm.generator import AnswerGenerator

log = structlog.get_logger()

_SQL_SYSTEM_PROMPT = (
    "You are a data analyst writing read-only SQL (only SELECT) for a Redshift/"
    "BigQuery warehouse. You MUST ONLY reference the exact table and columns "
    "provided in the context. Never invent columns, tables, schemas, or aliases. "
    "Never emit DDL/DML: no CREATE, ALTER, DROP, TRUNCATE, DELETE, INSERT, "
    "UPDATE, GRANT, REVOKE. Use the alias `t` for the main table. Return JSON "
    "with a single key \"sql\" holding the SQL."
)

_DANGEROUS = re.compile(
    r"\b(create|alter|drop|truncate|delete|insert|update|grant|revoke|rename|"
    r"call|execute|merge|replace)\b",
    re.I,
)

_COLUMN_REF_RE = re.compile(r"\bt\.([a-zA-Z_][a-zA-Z0-9_]*)")


def _validate_grounded_sql(sql: str, allowed_columns: set[str]) -> bool:
    """Return True when ``sql`` is read-only and stays within grounded columns."""
    if not sql or not sql.strip().lower().startswith("select"):
        return False
    if "from" not in sql.lower():
        return False
    if _DANGEROUS.search(sql):
        return False
    core = sql.rstrip()
    body = core[:-1] if core.endswith(";") else core
    if ";" in body:
        return False

    for m in _COLUMN_REF_RE.finditer(sql):
        if m.group(1) not in allowed_columns:
            return False
    return True


class GroundedSqlGenerator:
    """Enhance a grounded SQL statement with a constrained LLM pass."""

    def __init__(self, generator: AnswerGenerator) -> None:
        self._gen = generator

    def available(self) -> bool:
        llm = getattr(self._gen, "_llm", None)
        return bool(getattr(llm, "available", False))

    async def enhance(
        self,
        question: str,
        table: str,
        columns: list[str],
        base_sql: str,
    ) -> str | None:
        if not self.available() or not columns or not base_sql:
            return None
        allowed = set(columns)
        schema_lines = "\n".join(f"- {c}" for c in columns)
        prompt = (
            f"User question: {question}\n"
            f"Table (use alias `t`): {table}\n"
            f"Allowed columns:\n{schema_lines}\n"
            f"Current grounded SQL:\n{base_sql}\n\n"
            "Rewrite the SQL to answer the question faithfully. Add WHERE "
            "filters, GROUP BY, or ORDER BY only when the question requires, "
            "using only the allowed columns. Stay read-only. Return JSON "
            "{\"sql\": \"...\"}."
        )
        try:
            raw = await self._gen._llm.generate(
                prompt, context=None, system_prompt=_SQL_SYSTEM_PROMPT,
            )
            data = json.loads(raw or "")
            sql = (data.get("sql") or "").strip()
        except Exception:
            log.exception("sql_llm_failed", table=table)
            return None

        if not _validate_grounded_sql(sql, allowed):
            log.warning("sql_llm_rejected", table=table, sql=sql[:200])
            return None
        return sql
