from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from . import config
from .config import get_business_context, get_glossary
from .prompts import REACT_SYSTEM_PROMPT
from .state import AgentState
from .tools import ALL_TOOLS

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_API_BASE,
            model=config.OPENAI_MODEL,
            temperature=0,
        )
    return _llm


def _build_system_message() -> SystemMessage:
    glossary = get_glossary()
    business_context = get_business_context()
    prompt = REACT_SYSTEM_PROMPT.format(
        glossary=glossary,
        business_context=business_context,
    )
    return SystemMessage(content=prompt)


def agent_node(state: AgentState) -> dict:
    llm = _get_llm().bind_tools(ALL_TOOLS)
    system = _build_system_message()
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {"messages": [], "iterations": state.get("iterations", 0) + 1}

    tool_map = {t.name: t for t in ALL_TOOLS}
    results: list[ToolMessage] = []
    for tc in last_message.tool_calls:
        tool_fn = tool_map.get(tc["name"])
        if tool_fn is None:
            results.append(ToolMessage(
                content=f"Unknown tool: {tc['name']}",
                tool_call_id=tc["id"],
            ))
            continue
        try:
            output = tool_fn.invoke(tc["args"])
            results.append(ToolMessage(content=str(output), tool_call_id=tc["id"]))
        except Exception as e:
            results.append(ToolMessage(content=f"Error: {e}", tool_call_id=tc["id"]))

    return {"messages": results, "iterations": state.get("iterations", 0) + 1}


def should_continue(state: AgentState) -> str:
    if state.get("iterations", 0) >= config.MAX_ITERATIONS:
        return "end"
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"