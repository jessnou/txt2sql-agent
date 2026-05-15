from __future__ import annotations

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from . import config

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=config.CLICKHOUSE_HOST,
            port=config.CLICKHOUSE_PORT,
            username=config.CLICKHOUSE_USER,
            password=config.CLICKHOUSE_PASSWORD,
            database=config.CLICKHOUSE_DB,
        )
    return _client


def get_table_names(client: Client) -> list[str]:
    result = client.query("SHOW TABLES")
    return [row[0] for row in result.result_rows]


def get_schema_info(client: Client, table_names: list[str] | None = None) -> str:
    all_tables = get_table_names(client)
    target_tables = table_names if table_names else all_tables
    schemas: list[str] = []

    for table in target_tables:
        if table not in all_tables:
            continue
        cols_result = client.query(f"DESCRIBE TABLE {config.CLICKHOUSE_DB}.{table}")
        col_lines = []
        for row in cols_result.result_rows:
            col_name = row[0]
            col_type = row[1]
            col_lines.append(f"  {col_name} {col_type}")
        schemas.append(f"CREATE TABLE {table} (\n" + ",\n".join(col_lines) + "\n) ENGINE = MergeTree();")

    return "\n\n".join(schemas) if schemas else "No tables found."


def run_sql(client: Client, query: str) -> tuple[str, str]:
    try:
        result = client.query(query)
        rows = result.result_rows
        columns = result.column_names

        if not rows:
            return "Query returned 0 rows.", ""

        col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(columns))]
        col_widths = [max(len(col), w) for col, w in zip(columns, col_widths)]

        header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
        separator = "-+-".join("-" * w for w in col_widths)
        data_rows = "\n".join(
            " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(columns)))
            for row in rows
        )
        output = f"{header}\n{separator}\n{data_rows}\n\n({len(rows)} rows)"
        return output, ""
    except Exception as e:
        return "", str(e)