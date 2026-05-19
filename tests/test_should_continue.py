from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from txt2sql_agent.nodes import should_continue
from txt2sql_agent.state import AgentState
from txt2sql_agent import config


class TestShouldContinue:
    def test_no_tool_calls_returns_end(self):
        state = AgentState(
            messages=[HumanMessage(content="hello"), AIMessage(content="Привет!")],
            iterations=0,
            sql_review_count=0,
        )
        assert should_continue(state) == "end"

    def test_tool_calls_without_execute_sql_returns_tools(self):
        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "describe_table", "args": {"table_name": "metrics_facts"}, "id": "1"}],
        )
        state = AgentState(
            messages=[HumanMessage(content="опиши таблицу"), ai_msg],
            iterations=1,
            sql_review_count=0,
        )
        assert should_continue(state) == "tools"

    def test_execute_sql_under_limit_returns_review(self):
        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "execute_sql", "args": {"query": "SELECT 1"}, "id": "1"}],
        )
        state = AgentState(
            messages=[HumanMessage(content="запрос"), ai_msg],
            iterations=1,
            sql_review_count=0,
        )
        assert should_continue(state) == "review"

    def test_execute_sql_at_limit_returns_tools(self):
        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "execute_sql", "args": {"query": "SELECT 1"}, "id": "1"}],
        )
        state = AgentState(
            messages=[HumanMessage(content="запрос"), ai_msg],
            iterations=1,
            sql_review_count=config.MAX_SQL_REVIEW_ATTEMPTS,
        )
        assert should_continue(state) == "tools"

    def test_iterations_exceeded_returns_end(self):
        state = AgentState(
            messages=[HumanMessage(content="hello"), AIMessage(content="hi")],
            iterations=config.MAX_ITERATIONS,
            sql_review_count=0,
        )
        assert should_continue(state) == "end"

    def test_execute_sql_over_limit_returns_tools(self):
        ai_msg = AIMessage(
            content="",
            tool_calls=[{"name": "execute_sql", "args": {"query": "SELECT 1"}, "id": "1"}],
        )
        state = AgentState(
            messages=[HumanMessage(content="запрос"), ai_msg],
            iterations=1,
            sql_review_count=config.MAX_SQL_REVIEW_ATTEMPTS + 5,
        )
        assert should_continue(state) == "tools"