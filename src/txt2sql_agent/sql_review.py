from __future__ import annotations

from difflib import get_close_matches
from typing import TypedDict

import sqlglot
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from .prompts import SQL_FIX_PROMPT


class SqlIssue(TypedDict):
    severity: str
    message: str
    table: str | None
    column: str | None
    suggestion: str


class ReviewResult(TypedDict):
    sql: str
    changed: bool
    issues: list[SqlIssue]
    error: str | None


class SqlValidator:
    """Чистая AST-валидация SQL-запросов. Не зависит от БД и LLM."""

    @staticmethod
    def validate(sql: str, schema: dict[str, dict[str, str]]) -> list[SqlIssue]:
        """Проверить SQL на соответствие схеме: несуществующие таблицы и колонки.

        Args:
            sql: SQL-запрос для проверки.
            schema: Словарь {table: {column: type}} с известной схемой БД.

        Returns:
            Список найденных проблем (пустой, если запрос валиден).
        """
        issues: list[SqlIssue] = []
        known_tables = list(schema.keys())

        try:
            ast = sqlglot.parse_one(sql, dialect='clickhouse')
        except sqlglot.errors.ParseError as e:
            issues.append(SqlIssue(
                severity='error',
                message=f'SQL parse error: {e}',
                table=None,
                column=None,
                suggestion='Fix SQL syntax and try again',
            ))
            return issues

        alias_map = SqlValidator._build_alias_map(ast)

        SqlValidator._check_tables(ast, schema, known_tables, issues)
        SqlValidator._check_columns(ast, schema, alias_map, known_tables, issues)

        return issues

    @staticmethod
    def _check_tables(
        ast: sqlglot.Expression,
        schema: dict[str, dict[str, str]],
        known_tables: list[str],
        issues: list[SqlIssue],
    ) -> None:
        """Проверить существование таблиц в запросе."""
        for table_name in SqlValidator._extract_tables(ast):
            if table_name not in schema:
                matches = get_close_matches(table_name, known_tables, n=1, cutoff=0.6)
                suggestion = f'Did you mean {matches[0]}?' if matches else ''
                issues.append(SqlIssue(
                    severity='error',
                    message=f"Table '{table_name}' does not exist",
                    table=table_name,
                    column=None,
                    suggestion=suggestion,
                ))

    @staticmethod
    def _check_columns(
        ast: sqlglot.Expression,
        schema: dict[str, dict[str, str]],
        alias_map: dict[str, str],
        known_tables: list[str],
        issues: list[SqlIssue],
    ) -> None:
        """Проверить существование колонок в контексте их таблиц."""
        tables_in_sql = SqlValidator._extract_tables(ast)

        for table_alias, col_name in SqlValidator._extract_columns_with_tables(ast):
            if col_name == '*':
                continue

            resolved_table = SqlValidator._resolve_alias(table_alias, alias_map)
            possible_tables = (
                [resolved_table] if resolved_table
                else [t for t in tables_in_sql if t in schema]
            )

            found = False
            for tbl in possible_tables:
                if tbl in schema and col_name in schema[tbl]:
                    found = True
                    break

            if not found and possible_tables:
                for tbl in possible_tables:
                    if tbl in schema:
                        col_matches = get_close_matches(
                            col_name, list(schema[tbl].keys()), n=1, cutoff=0.6,
                        )
                        suggestion = f'Did you mean {col_matches[0]}?' if col_matches else ''
                        issues.append(SqlIssue(
                            severity='error',
                            message=f"Column '{col_name}' does not exist in table '{tbl}'",
                            table=tbl,
                            column=col_name,
                            suggestion=suggestion,
                        ))
                        break

    @staticmethod
    def _extract_tables(ast: sqlglot.Expression) -> list[str]:
        """Извлечь все имена таблиц из AST."""
        tables: list[str] = []
        for table in ast.find_all(sqlglot.exp.Table):
            name = table.name
            if name:
                tables.append(name)
        return tables

    @staticmethod
    def _extract_columns_with_tables(ast: sqlglot.Expression) -> list[tuple[str | None, str]]:
        """Извлечь все колонки с их табличными префиксами из AST."""
        columns: list[tuple[str | None, str]] = []
        for col in ast.find_all(sqlglot.exp.Column):
            table_name = col.table if col.table else None
            columns.append((table_name, col.name))
        return columns

    @staticmethod
    def _resolve_alias(table_alias: str | None, alias_map: dict[str, str]) -> str | None:
        """Разрешить алиас таблицы в реальное имя."""
        if table_alias is None:
            return None
        return alias_map.get(table_alias.lower(), table_alias)

    @staticmethod
    def _build_alias_map(ast: sqlglot.Expression) -> dict[str, str]:
        """Построить маппинг алиас → реальное имя таблицы."""
        alias_map: dict[str, str] = {}
        for table in ast.find_all(sqlglot.exp.Table):
            alias = table.alias
            if alias:
                alias_map[alias.lower()] = table.name
        return alias_map


class SqlFixer:
    """Исправление SQL-запросов через LLM."""

    def __init__(self, llm: ChatOpenAI) -> None:
        self._llm = llm

    def fix(self, sql: str, issues: list[SqlIssue], schema_ddl: str) -> ReviewResult:
        """Попытаться исправить SQL с помощью LLM.

        Args:
            sql: Исходный SQL-запрос с проблемами.
            issues: Список обнаруженных проблем.
            schema_ddl: DDL-описание схемы для контекста LLM.

        Returns:
            ReviewResult с исправленным SQL (changed=True) или
            с исходным (changed=False), если LLM не смог исправить.
        """
        issues_text = '\n'.join(
            f"- [{i['severity']}] {i['message']}"
            + (f" (suggestion: {i['suggestion']})" if i.get('suggestion') else '')
            for i in issues
        )

        prompt = SQL_FIX_PROMPT.format(sql=sql, issues=issues_text, schema=schema_ddl)

        response = self._llm.invoke([SystemMessage(content=prompt)])
        fixed_sql = SqlFixer._strip_markdown_sql(response.content)

        if fixed_sql.strip() == sql.strip():
            return ReviewResult(sql=sql, changed=False, issues=issues, error=None)

        return ReviewResult(sql=fixed_sql, changed=True, issues=issues, error=None)

    @staticmethod
    def _strip_markdown_sql(text: str) -> str:
        """Удалить markdown-обёртки ```sql ... ``` из ответа LLM."""
        text = text.strip()
        if text.startswith('```sql'):
            text = text[6:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        return text.strip()


class SqlReviewService:
    """Оркестратор SQL-ревью: validate → fix → verify."""

    def __init__(
        self,
        schema_repo: 'SchemaRepository',
        validator: SqlValidator,
        fixer: SqlFixer,
    ) -> None:
        self._schema_repo = schema_repo
        self._validator = validator
        self._fixer = fixer

    def review_and_fix(self, sql: str) -> ReviewResult:
        """Проверить и при необходимости исправить SQL-запрос.

        Пайплайн:
        1. Статическая валидация (AST) через SqlValidator.
        2. Если проблем нет — вернуть исходный SQL без изменений.
        3. Если проблемы есть — попытка LLM-исправления через SqlFixer.
        4. Если LLM не смог исправить — вернуть исходный SQL с проблемами.
        5. Если LLM исправил — EXPLAIN-верификация через SchemaRepository.
        6. Если EXPLAIN прошёл — вернуть исправленный SQL.
        7. Если EXPLAIN не прошёл — вернуть исходный SQL с ошибкой.
        """
        schema = self._schema_repo.get_schema()
        issues = self._validator.validate(sql, schema)

        if not issues:
            return ReviewResult(sql=sql, changed=False, issues=[], error=None)

        schema_ddl = self._schema_repo.schema_to_ddl()
        fix_result = self._fixer.fix(sql, issues, schema_ddl)

        if not fix_result['changed']:
            return ReviewResult(sql=sql, changed=False, issues=issues, error=None)

        ok, err = self._schema_repo.verify_sql(fix_result['sql'])
        if ok:
            return ReviewResult(sql=fix_result['sql'], changed=True, issues=issues, error=None)

        return ReviewResult(sql=sql, changed=False, issues=issues, error=err)