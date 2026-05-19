from __future__ import annotations

import pytest

from tests.conftest import (
    VALID_SQL_SIMPLE,
    VALID_SQL_JOIN,
    VALID_SQL_SUBQUERY,
    INVALID_SQL_TABLE,
    INVALID_SQL_COLUMN,
    MULTIPLE_ISSUES_SQL,
    FUZZY_TABLE_SQL,
    FUZZY_COLUMN_SQL,
    ALIAS_SQL,
    STAR_SQL,
    SUBQUERY_BAD_TABLE_SQL,
    MOCK_SCHEMA,
)
from txt2sql_agent.sql_review import SqlValidator, SqlIssue


class TestValidateValidQueries:
    def test_valid_simple_query(self, validator):
        issues = validator.validate(VALID_SQL_SIMPLE, MOCK_SCHEMA)
        assert issues == []

    def test_valid_join_query(self, validator):
        issues = validator.validate(VALID_SQL_JOIN, MOCK_SCHEMA)
        assert issues == []

    def test_valid_subquery(self, validator):
        issues = validator.validate(VALID_SQL_SUBQUERY, MOCK_SCHEMA)
        assert issues == []

    def test_valid_alias_resolution(self, validator):
        issues = validator.validate(ALIAS_SQL, MOCK_SCHEMA)
        assert issues == []

    def test_valid_star_select(self, validator):
        issues = validator.validate(STAR_SQL, MOCK_SCHEMA)
        assert issues == []


class TestValidateNonexistentTable:
    def test_nonexistent_table_error(self, validator):
        issues = validator.validate(INVALID_SQL_TABLE, MOCK_SCHEMA)
        assert len(issues) >= 1
        table_issues = [i for i in issues if "nonexistent_table" in i["message"].lower() or i["table"] == "nonexistent_table"]
        assert len(table_issues) >= 1
        assert table_issues[0]["severity"] == "error"

    def test_fuzzy_table_match_suggestion(self, validator):
        issues = validator.validate(FUZZY_TABLE_SQL, MOCK_SCHEMA)
        assert len(issues) >= 1
        table_issues = [i for i in issues if i["severity"] == "error"]
        assert any("metrics_facts" in i["suggestion"] for i in table_issues)


class TestValidateNonexistentColumn:
    def test_nonexistent_column_error(self, validator):
        issues = validator.validate(INVALID_SQL_COLUMN, MOCK_SCHEMA)
        assert len(issues) >= 1
        col_issues = [i for i in issues if i["column"] == "wrong_column"]
        assert len(col_issues) >= 1
        assert col_issues[0]["severity"] == "error"

    def test_fuzzy_column_match_suggestion(self, validator):
        issues = validator.validate(FUZZY_COLUMN_SQL, MOCK_SCHEMA)
        assert len(issues) >= 1
        col_issues = [i for i in issues if i["column"] == "metric_idd" and i["severity"] == "error"]
        assert len(col_issues) >= 1
        assert any("metric_id" in i["suggestion"] for i in col_issues)


class TestValidateMultipleIssues:
    def test_multiple_issues_detected(self, validator):
        issues = validator.validate(MULTIPLE_ISSUES_SQL, MOCK_SCHEMA)
        assert len(issues) >= 1

    def test_subquery_nonexistent_table(self, validator):
        issues = validator.validate(SUBQUERY_BAD_TABLE_SQL, MOCK_SCHEMA)
        assert len(issues) >= 1
        table_issues = [i for i in issues if "wrong_dict" in (i["table"] or "") or "wrong_dict" in i["message"].lower()]
        assert len(table_issues) >= 1
        assert table_issues[0]["severity"] == "error"