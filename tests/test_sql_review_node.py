from __future__ import annotations

from unittest.mock import patch, MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from txt2sql_agent.nodes import sql_review_node
from txt2sql_agent.sql_review import SqlReviewService, SqlValidator, SqlFixer, ReviewResult, SqlIssue
from txt2sql_agent.schema_repository import SchemaRepository
from txt2sql_agent.state import AgentState
from txt2sql_agent import config


class TestSqlReviewNode:
    @patch('txt2sql_agent.config._SQL_REVIEW_SERVICE')
    def test_review_changes_sql(self, mock_service_attr):
        original_sql = "SELECT * FROM metrics_facts WHERE lower(struct_code) = 'test'"
        fixed_sql = "SELECT * FROM metrics_facts WHERE lowerUTF8(struct_code) = 'test'"

        mock_service = MagicMock(spec=SqlReviewService)
        mock_service.review_and_fix.return_value = ReviewResult(
            sql=fixed_sql,
            changed=True,
            issues=[SqlIssue(severity="warning", message="Use lowerUTF8()", table="metrics_facts", column="struct_code", suggestion="Replace lower() with lowerUTF8()")],
        )
        mock_service_attr.__class__ = SqlReviewService

        with patch('txt2sql_agent.nodes.get_sql_review_service', return_value=mock_service):
            ai_msg = AIMessage(
                content="",
                tool_calls=[{"name": "execute_sql", "args": {"query": original_sql}, "id": "call_1"}],
            )
            state = AgentState(
                messages=[HumanMessage(content="запрос"), ai_msg],
                iterations=1,
                sql_review_count=0,
            )

            result = sql_review_node(state)
            assert result["sql_review_count"] == 1
            system_msgs = [m for m in result["messages"] if isinstance(m, SystemMessage)]
            assert any("SQL Review" in m.content for m in system_msgs)
            assert any("исправлено" in m.content for m in system_msgs)

    @patch('txt2sql_agent.config._SQL_REVIEW_SERVICE')
    def test_review_passes_valid_sql(self, mock_service_attr):
        valid_sql = "SELECT metric_id FROM metrics_facts WHERE metric_id = 1"

        mock_service = MagicMock(spec=SqlReviewService)
        mock_service.review_and_fix.return_value = ReviewResult(sql=valid_sql, changed=False, issues=[])

        with patch('txt2sql_agent.nodes.get_sql_review_service', return_value=mock_service):
            ai_msg = AIMessage(
                content="",
                tool_calls=[{"name": "execute_sql", "args": {"query": valid_sql}, "id": "call_1"}],
            )
            state = AgentState(
                messages=[HumanMessage(content="запрос"), ai_msg],
                iterations=1,
                sql_review_count=0,
            )

            result = sql_review_node(state)
            assert result["sql_review_count"] == 1

    @patch('txt2sql_agent.config._SQL_REVIEW_SERVICE')
    def test_review_with_error(self, mock_service_attr):
        bad_sql = "SELECT * FROM nonexistent"

        mock_service = MagicMock(spec=SqlReviewService)
        mock_service.review_and_fix.return_value = ReviewResult(
            sql=bad_sql,
            changed=False,
            issues=[SqlIssue(severity="error", message="Table nonexistent doesn't exist", table="nonexistent", column=None, suggestion="")],
            error="Table nonexistent doesn't exist",
        )

        with patch('txt2sql_agent.nodes.get_sql_review_service', return_value=mock_service):
            ai_msg = AIMessage(
                content="",
                tool_calls=[{"name": "execute_sql", "args": {"query": bad_sql}, "id": "call_1"}],
            )
            state = AgentState(
                messages=[HumanMessage(content="запрос"), ai_msg],
                iterations=1,
                sql_review_count=0,
            )

            result = sql_review_node(state)
            assert result["sql_review_count"] == 1
            system_msgs = [m for m in result["messages"] if isinstance(m, SystemMessage)]
            assert any("не удалось" in m.content for m in system_msgs)

    def test_review_skipped_over_limit(self):
        original_sql = "SELECT lower(x) FROM t"

        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "execute_sql", "args": {"query": original_sql}, "id": "call_1"}],
        )
        state = AgentState(
            messages=[HumanMessage(content="запрос"), ai_msg],
            iterations=1,
            sql_review_count=config.MAX_SQL_REVIEW_ATTEMPTS,
        )

        with patch('txt2sql_agent.nodes.get_sql_review_service') as mock_get_service:
            result = sql_review_node(state)
            mock_get_service.assert_not_called()

        assert result["sql_review_count"] == config.MAX_SQL_REVIEW_ATTEMPTS
        assert result["iterations"] == 2

    @patch('txt2sql_agent.config._SQL_REVIEW_SERVICE')
    def test_mixed_tool_calls(self, mock_service_attr):
        original_sql = "SELECT * FROM metrics_facts"
        fixed_sql = "SELECT * FROM metrics_facts WHERE metric_id = 1"

        mock_service = MagicMock(spec=SqlReviewService)
        mock_service.review_and_fix.return_value = ReviewResult(
            sql=fixed_sql,
            changed=True,
            issues=[SqlIssue(severity="warning", message="Use lowerUTF8() instead of lower()", table="metrics_facts", column="struct_code", suggestion="Replace lower() with lowerUTF8()")],
        )

        with patch('txt2sql_agent.nodes.get_sql_review_service', return_value=mock_service):
            ai_msg = AIMessage(
                content="",
                tool_calls=[
                    {"name": "describe_table", "args": {"table_name": "metrics_facts"}, "id": "call_1"},
                    {"name": "execute_sql", "args": {"query": original_sql}, "id": "call_2"},
                ],
            )
            state = AgentState(
                messages=[HumanMessage(content="запрос"), ai_msg],
                iterations=1,
                sql_review_count=0,
            )

            result = sql_review_node(state)
            assert result["sql_review_count"] == 1
            ai_msgs = [m for m in result["messages"] if isinstance(m, AIMessage)]
            assert len(ai_msgs) == 1
            tc_names = [tc["name"] for tc in ai_msgs[0].tool_calls]
            assert "describe_table" in tc_names
            assert "execute_sql" in tc_names

    def test_no_execute_sql_tool_call(self):
        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "describe_table", "args": {"table_name": "metrics_facts"}, "id": "call_1"}],
        )
        state = AgentState(
            messages=[HumanMessage(content="опиши таблицу"), ai_msg],
            iterations=1,
            sql_review_count=0,
        )

        with patch('txt2sql_agent.nodes.get_sql_review_service') as mock_get_service:
            result = sql_review_node(state)
            mock_get_service.assert_not_called()

        assert result["sql_review_count"] == 0
        assert result["iterations"] == 2