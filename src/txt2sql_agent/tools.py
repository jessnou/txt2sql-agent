from __future__ import annotations

from langchain_core.tools import tool

from .db import get_client, run_sql


@tool
def list_tables() -> str:
    """List all tables in the ClickHouse database.
    Use this first to understand what tables are available."""
    client = get_client()
    result = client.query("SHOW TABLES")
    tables = [row[0] for row in result.result_rows]
    return f"Tables in database: {', '.join(tables)}"


@tool
def describe_table(table_name: str) -> str:
    """Get column names and types for a specific table.
    Use this to understand the schema before writing queries.

    Args:
        table_name: Name of the table to describe (e.g. 'metrics_facts', 'metrics_dict', 'struct_code')
    """
    client = get_client()
    try:
        result = client.query(f"DESCRIBE TABLE {table_name}")
        lines = []
        for row in result.result_rows:
            lines.append(f"  {row[0]} {row[1]}")
        return f"Table {table_name}:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error describing table {table_name}: {e}"


@tool
def search_metrics(query: str) -> str:
    """Search metrics by keyword (supports Russian).
    Use when the user mentions a metric by slang, abbreviation, or partial name.
    Returns matching metric_id and metric_name pairs.

    Args:
        query: Keyword to search in metric names (e.g. 'боевая', 'текучесть', 'скм')
    """
    client = get_client()
    try:
        sql = f"SELECT DISTINCT metric_id, metric_name FROM metrics_dict WHERE lowerUTF8(metric_name) LIKE lowerUTF8('%{query}%') ORDER BY metric_id"
        result = client.query(sql)
        if not result.result_rows:
            return f"No metrics found matching '{query}'. Try a different keyword."
        lines = [f"  metric_id={row[0]}: {row[1]}" for row in result.result_rows]
        return "Matching metrics:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error searching metrics: {e}"


@tool
def sample_data(table_name: str, n: int = 5) -> str:
    """Get sample rows from a table to understand data format and content.

    Args:
        table_name: Name of the table to sample
        n: Number of rows to return (default 5, max 20)
    """
    client = get_client()
    n = min(n, 20)
    try:
        result = client.query(f"SELECT * FROM {table_name} LIMIT {n}")
        columns = result.column_names
        rows = result.result_rows
        if not rows:
            return f"Table {table_name} is empty."

        col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(columns))]
        col_widths = [max(len(col), w) for col, w in zip(columns, col_widths)]

        header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
        separator = "-+-".join("-" * w for w in col_widths)
        data_rows = "\n".join(
            " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(columns)))
            for row in rows
        )
        return f"Sample from {table_name} ({n} rows):\n{header}\n{separator}\n{data_rows}"
    except Exception as e:
        return f"Error sampling {table_name}: {e}"


@tool
def get_distinct_values(table_name: str, column_name: str) -> str:
    """Get distinct values for a column.
    Use to discover valid filter values (e.g. metric_level, period_type, metric_type).

    Args:
        table_name: Name of the table
        column_name: Name of the column to get distinct values for
    """
    client = get_client()
    try:
        result = client.query(f"SELECT DISTINCT `{column_name}` FROM {table_name} ORDER BY `{column_name}`")
        values = [str(row[0]) for row in result.result_rows]
        return f"Distinct values of {table_name}.{column_name}: {', '.join(values)}"
    except Exception as e:
        return f"Error getting distinct values for {table_name}.{column_name}: {e}"


@tool
def get_date_range(table_name: str, column_name: str) -> str:
    """Get min and max date values for a date column.
    Use to understand the time range of available data.

    Args:
        table_name: Name of the table
        column_name: Name of the date column (e.g. 'report_dt')
    """
    client = get_client()
    try:
        result = client.query(f"SELECT min(`{column_name}`), max(`{column_name}`) FROM {table_name}")
        min_val, max_val = result.result_rows[0]
        return f"Date range of {table_name}.{column_name}: {min_val} to {max_val}"
    except Exception as e:
        return f"Error getting date range for {table_name}.{column_name}: {e}"


@tool
def execute_sql(query: str) -> str:
    """Execute a ClickHouse SQL query and return results.
    Use this for the final analytical query after you've explored the schema and found the right metric_id.
    For month-end dates use the last day of month (e.g. '2025-01-31', '2025-02-28').

    Args:
        query: ClickHouse SQL query to execute
    """
    client = get_client()
    result, error = run_sql(client, query)
    if error:
        return f"SQL Error: {error}\n\nFix the query and try again."
    return result


ALL_TOOLS = [list_tables, describe_table, search_metrics, sample_data, get_distinct_values, get_date_range, execute_sql]