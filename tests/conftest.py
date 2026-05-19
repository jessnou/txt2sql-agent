from __future__ import annotations

import pytest
from unittest.mock import MagicMock

import clickhouse_connect.driver

from txt2sql_agent.schema_repository import SchemaRepository
from txt2sql_agent.sql_review import SqlFixer, SqlValidator, SqlReviewService

MOCK_SCHEMA = {
    'metrics_facts': {
        'metric_id': 'Int32',
        'metric_level': 'LowCardinality(String)',
        'struct_code': 'String',
        'period_type': 'LowCardinality(String)',
        'metric_type': 'LowCardinality(String)',
        'report_dt': 'Date',
        'value': 'Float64',
    },
    'metrics_dict': {
        'metric_id': 'Int32',
        'metric_name': 'String',
    },
    'struct_code': {
        'struct_code': 'String',
        'struct_lvl': 'LowCardinality(String)',
        'tb_id': 'String',
        'gosb_id': 'String',
        'tb_name': 'String',
        'gosb_name': 'String',
        'vsp_name': 'String',
    },
}

MOCK_DDL = """\
CREATE TABLE metrics_facts (
  metric_id Int32,
  metric_level LowCardinality(String),
  struct_code String,
  period_type LowCardinality(String),
  metric_type LowCardinality(String),
  report_dt Date,
  value Float64
);
CREATE TABLE metrics_dict (
  metric_id Int32,
  metric_name String
);
CREATE TABLE struct_code (
  struct_code String,
  struct_lvl LowCardinality(String),
  tb_id String,
  gosb_id String,
  tb_name String,
  gosb_name String,
  vsp_name String
);"""

MOCK_TABLES = ['metrics_facts', 'metrics_dict', 'struct_code']

VALID_SQL_SIMPLE = "SELECT metric_id, SUM(value) FROM metrics_facts WHERE metric_id = 1 AND report_dt = '2025-01-31' GROUP BY metric_id"

VALID_SQL_JOIN = "SELECT mf.metric_id FROM metrics_facts mf JOIN metrics_dict md ON mf.metric_id = md.metric_id WHERE mf.report_dt = '2025-02-28'"

VALID_SQL_SUBQUERY = "SELECT * FROM metrics_facts WHERE metric_id IN (SELECT metric_id FROM metrics_dict WHERE metric_id = 5)"

INVALID_SQL_TABLE = "SELECT * FROM nonexistent_table"

INVALID_SQL_COLUMN = "SELECT mf.wrong_column FROM metrics_facts mf"

MULTIPLE_ISSUES_SQL = ("SELECT mf.wrong_col FROM metrics_facts mf "
                       "WHERE lower(mf.struct_code) = 'test'")

FUZZY_TABLE_SQL = "SELECT * FROM metric_facts WHERE metric_id = 1"

FUZZY_COLUMN_SQL = "SELECT mf.metric_idd FROM metrics_facts mf"

ALIAS_SQL = "SELECT mf.value FROM metrics_facts mf WHERE mf.metric_id = 1"

STAR_SQL = "SELECT * FROM metrics_facts WHERE metric_id = 1"

SUBQUERY_BAD_TABLE_SQL = ("SELECT * FROM metrics_facts WHERE metric_id IN "
                          "(SELECT id FROM wrong_dict)")


def _make_mock_ch_client(schema=None, tables=None):
    """Создать MagicMock ClickHouse-клиента для SchemaRepository."""
    schema = schema or MOCK_SCHEMA
    tables = tables or MOCK_TABLES
    client = MagicMock(spec=clickhouse_connect.driver.Client)

    def mock_query(sql):
        result = MagicMock()
        sql_lower = sql.strip().lower()

        if sql_lower == 'show tables':
            result.result_rows = [(t,) for t in tables]
            result.column_names = ['name']
            return result

        if sql_lower.startswith('describe table'):
            table_name = sql.strip().split()[-1].strip('`;')
            if table_name in schema:
                result.result_rows = [(col, typ) for col, typ in schema[table_name].items()]
                result.column_names = ['name', 'type']
                return result
            raise Exception(f"Table {table_name} doesn't exist")

        if sql_lower.startswith('explain'):
            return result

        return result

    client.query = MagicMock(side_effect=mock_query)
    return client


@pytest.fixture
def mock_schema():
    return MOCK_SCHEMA


@pytest.fixture
def mock_ddl():
    return MOCK_DDL


@pytest.fixture
def mock_tables():
    return MOCK_TABLES


@pytest.fixture
def mock_ch_client():
    return _make_mock_ch_client()


@pytest.fixture
def validator():
    return SqlValidator()


@pytest.fixture
def schema_repo(mock_ch_client):
    return SchemaRepository(mock_ch_client)


@pytest.fixture
def mock_llm():
    from langchain_core.messages import AIMessage
    llm = MagicMock()
    return llm


@pytest.fixture
def fixer(mock_llm):
    return SqlFixer(mock_llm)


@pytest.fixture
def review_service(schema_repo, validator, fixer):
    return SqlReviewService(schema_repo, validator, fixer)