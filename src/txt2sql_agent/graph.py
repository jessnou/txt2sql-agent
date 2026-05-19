from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import agent_node, should_continue, sql_review_node, tool_node
from .state import AgentState


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_node("sql_review", sql_review_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "review": "sql_review", "end": END},
    )
    builder.add_edge("sql_review", "tools")
    builder.add_edge("tools", "agent")

    return builder.compile()