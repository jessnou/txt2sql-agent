from __future__ import annotations

from langgraph.graph import add_messages
from typing_extensions import Annotated, TypedDict

from langchain_core.messages import AnyMessage


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    iterations: int
    sql_review_count: int