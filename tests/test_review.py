from __future__ import annotations

from unittest.mock import MagicMock

from txt2sql_agent.sql_review import SqlReviewService, SqlValidator, SqlFixer, SqlIssue, ReviewResult
from txt2sql_agent.schema_repository import SchemaRepository
from tests.conftest import MOCK_SCHEMA, VALID_SQL_SIMPLE


class TestReviewAndFix:

    def test_no_issues_pass_through(self, review_service):
        original_service = review_service
        schema_repo = MagicMock(spec=SchemaRepository)
        schema_repo.get_schema.return_value = MOCK_SCHEMA
        validator = MagicMock(spec=SqlValidator)
        validator.validate.return_value = []
        fixer = MagicMock(spec=SqlFixer)
        service = SqlReviewService(schema_repo, validator, fixer)

        result = service.review_and_fix(VALID_SQL_SIMPLE)
        assert result["changed"] is False
        assert result["sql"] == VALID_SQL_SIMPLE
        fixer.fix.assert_not_called()

    def test_issues_fixed_explain_ok(self):
        original_sql = "SELECT mf.wrong_col FROM metrics_facts mf"
        fixed_sql = "SELECT mf.metric_id FROM metrics_facts mf"
        issues = [SqlIssue(severity="error", message="Column 'wrong_col' does not exist", table="metrics_facts", column="wrong_col", suggestion="Did you mean metric_id?")]

        schema_repo = MagicMock(spec=SchemaRepository)
        schema_repo.get_schema.return_value = MOCK_SCHEMA
        schema_repo.schema_to_ddl.return_value = "CREATE TABLE ..."
        schema_repo.verify_sql.return_value = (True, "")

        validator = MagicMock(spec=SqlValidator)
        validator.validate.return_value = issues

        fixer = MagicMock(spec=SqlFixer)
        fixer.fix.return_value = ReviewResult(sql=fixed_sql, changed=True, issues=issues)

        service = SqlReviewService(schema_repo, validator, fixer)
        result = service.review_and_fix(original_sql)
        assert result["changed"] is True
        assert result["sql"] == fixed_sql
        assert len(result["issues"]) == 1

    def test_issues_fixed_explain_fail(self):
        original_sql = "SELECT mf.wrong_col FROM metrics_facts mf"
        fixed_sql = "SELECT mf.metric_id FROM metrics_facts mf"
        issues = [SqlIssue(severity="error", message="Column 'wrong_col' does not exist", table="metrics_facts", column="wrong_col", suggestion="Did you mean metric_id?")]

        schema_repo = MagicMock(spec=SchemaRepository)
        schema_repo.get_schema.return_value = MOCK_SCHEMA
        schema_repo.schema_to_ddl.return_value = "CREATE TABLE ..."
        schema_repo.verify_sql.return_value = (False, "Syntax error in fixed SQL")

        validator = MagicMock(spec=SqlValidator)
        validator.validate.return_value = issues

        fixer = MagicMock(spec=SqlFixer)
        fixer.fix.return_value = ReviewResult(sql=fixed_sql, changed=True, issues=issues)

        service = SqlReviewService(schema_repo, validator, fixer)
        result = service.review_and_fix(original_sql)
        assert result["changed"] is False
        assert result["sql"] == original_sql
        assert result["error"] is not None

    def test_llm_returns_same_sql(self):
        original_sql = "SELECT mf.wrong_col FROM metrics_facts mf"
        issues = [SqlIssue(severity="error", message="Column 'wrong_col' does not exist", table="metrics_facts", column="wrong_col", suggestion="Did you mean metric_id?")]

        schema_repo = MagicMock(spec=SchemaRepository)
        schema_repo.get_schema.return_value = MOCK_SCHEMA
        schema_repo.schema_to_ddl.return_value = "CREATE TABLE ..."

        validator = MagicMock(spec=SqlValidator)
        validator.validate.return_value = issues

        fixer = MagicMock(spec=SqlFixer)
        fixer.fix.return_value = ReviewResult(sql=original_sql, changed=False, issues=issues)

        service = SqlReviewService(schema_repo, validator, fixer)
        result = service.review_and_fix(original_sql)
        assert result["changed"] is False
        assert result["sql"] == original_sql
        schema_repo.verify_sql.assert_not_called()

    def test_multiple_issues_fixed(self):
        two_issues = [
            SqlIssue(severity="error", message="Column 'wrong_col' does not exist", table="metrics_facts", column="wrong_col", suggestion="Did you mean: value?"),
            SqlIssue(severity="error", message="Table 'nonexist' does not exist", table="nonexist", column=None, suggestion=""),
        ]

        schema_repo = MagicMock(spec=SchemaRepository)
        schema_repo.get_schema.return_value = MOCK_SCHEMA
        schema_repo.schema_to_ddl.return_value = "CREATE TABLE ..."
        schema_repo.verify_sql.return_value = (True, "")

        validator = MagicMock(spec=SqlValidator)
        validator.validate.return_value = two_issues

        fixed_sql = "SELECT mf.value FROM metrics_facts mf"
        fixer = MagicMock(spec=SqlFixer)
        fixer.fix.return_value = ReviewResult(sql=fixed_sql, changed=True, issues=two_issues)

        service = SqlReviewService(schema_repo, validator, fixer)
        result = service.review_and_fix("SELECT mf.wrong_col FROM nonexist mf")
        assert result["changed"] is True
        assert len(result["issues"]) == 2