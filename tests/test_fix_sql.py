from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from txt2sql_agent.sql_review import SqlFixer, SqlIssue, ReviewResult
from tests.conftest import MOCK_DDL


class TestFixSqlWithLlm:
    def test_fix_wrong_column(self, fixer, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content="SELECT mf.metric_id FROM metrics_facts mf"
        )

        issues = [
            SqlIssue(severity="error", message="Column 'wrong_column' does not exist", table="metrics_facts", column="wrong_column", suggestion="Did you mean: metric_id, ...")
        ]

        result = fixer.fix(
            "SELECT mf.wrong_column FROM metrics_facts mf",
            issues,
            MOCK_DDL,
        )
        assert result["changed"] is True
        assert "wrong_column" not in result["sql"]
        assert "metric_id" in result["sql"]

    def test_llm_returns_original_sql(self, fixer, mock_llm):
        original_sql = "SELECT * FROM metrics_facts WHERE metric_id = 1"
        mock_llm.invoke.return_value = MagicMock(content=original_sql)

        issues = [
            SqlIssue(severity="error", message="Column 'wrong_col' does not exist", table="metrics_facts", column="wrong_col", suggestion="Did you mean: value?")
        ]

        result = fixer.fix(original_sql, issues, MOCK_DDL)
        assert result["changed"] is False
        assert result["sql"] == original_sql

    def test_llm_returns_markdown_stripped(self, fixer, mock_llm):
        mock_llm.invoke.return_value = MagicMock(
            content="```sql\nSELECT metric_id FROM metrics_facts WHERE metric_id = 1\n```"
        )

        issues = [
            SqlIssue(severity="error", message="Column 'wrong_col' does not exist", table="metrics_facts", column="wrong_col", suggestion="Did you mean: metric_id?")
        ]

        result = fixer.fix(
            "SELECT wrong_col FROM metrics_facts",
            issues,
            MOCK_DDL,
        )
        assert result["changed"] is True
        assert not result["sql"].startswith("```")
        assert not result["sql"].endswith("```")