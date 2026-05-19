from __future__ import annotations

from clickhouse_connect.driver.client import Client


class SchemaRepository:
    """Инкапсулирует доступ к схеме ClickHouse: загрузка таблиц, колонок, EXPLAIN-проверка."""

    def __init__(self, client: Client) -> None:
        self._client = client
        self._schema: dict[str, dict[str, str]] | None = None
        self._tables: list[str] | None = None

    def get_table_names(self) -> list[str]:
        """Вернуть список таблиц из БД (с кэшированием)."""
        if self._tables is not None:
            return self._tables

        result = self._client.query('SHOW TABLES')
        self._tables = [row[0] for row in result.result_rows]
        return self._tables

    def get_schema(self) -> dict[str, dict[str, str]]:
        """Вернуть {table: {column: type}} из БД (с кэшированием)."""
        if self._schema is not None:
            return self._schema

        tables = self.get_table_names()
        schema: dict[str, dict[str, str]] = {}
        for table in tables:
            result = self._client.query(f'DESCRIBE TABLE {table}')
            schema[table] = {row[0]: row[1] for row in result.result_rows}

        self._schema = schema
        return self._schema

    def schema_to_ddl(self) -> str:
        """Сериализовать схему в DDL-строку для LLM-промпта."""
        schema = self.get_schema()
        parts: list[str] = []
        for table_name, columns in schema.items():
            col_lines = ', '.join(f'{col} {typ}' for col, typ in columns.items())
            parts.append(f'CREATE TABLE {table_name} ({col_lines})')
        return '\n'.join(parts)

    def verify_sql(self, sql: str) -> tuple[bool, str]:
        """EXPLAIN <sql> — проверить валидность запроса через ClickHouse."""
        try:
            self._client.query(f'EXPLAIN {sql}')
            return True, ''
        except Exception as e:
            return False, str(e)