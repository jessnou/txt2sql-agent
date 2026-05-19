from __future__ import annotations

import copy

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from . import config
from .config import get_business_context, get_glossary, get_sql_review_service
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


def sql_review_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {"iterations": state.get("iterations", 0) + 1, "sql_review_count": state.get("sql_review_count", 0)}

    if state.get("sql_review_count", 0) >= config.MAX_SQL_REVIEW_ATTEMPTS:
        return {"iterations": state.get("iterations", 0) + 1, "sql_review_count": state.get("sql_review_count", 0)}

    has_execute_sql = any(tc["name"] == "execute_sql" for tc in last_message.tool_calls)
    if not has_execute_sql:
        return {"iterations": state.get("iterations", 0) + 1, "sql_review_count": state.get("sql_review_count", 0)}

    new_messages: list = []
    new_tool_calls = []
    review_messages: list[SystemMessage] = []

    for tc in last_message.tool_calls:
        if tc["name"] == "execute_sql":
            sql = tc["args"].get("query", "")
            review_result = get_sql_review_service().review_and_fix(sql)

            if review_result["changed"]:
                new_tc = copy.deepcopy(tc)
                new_tc["args"]["query"] = review_result["sql"]
                new_tool_calls.append(new_tc)
                issues_text = "; ".join(i["message"] for i in review_result["issues"])
                review_messages.append(SystemMessage(
                    content=f"SQL Review: исправлено {len(review_result['issues'])} проблем(ы): {issues_text}. Исправленный SQL: {review_result['sql']}"
                ))
            elif review_result.get("error"):
                new_tool_calls.append(tc)
                review_messages.append(SystemMessage(
                    content=f"SQL Review: обнаружены проблемы, но не удалось автоматически исправить: {review_result['error']}"
                ))
            else:
                new_tool_calls.append(tc)
                if review_result.get("issues"):
                    issues_text = "; ".join(i["message"] for i in review_result["issues"])
                    review_messages.append(SystemMessage(
                        content=f"SQL Review: SQL прошёл проверку, но есть предупреждения: {issues_text}"
                    ))
        else:
            new_tool_calls.append(tc)

    if review_messages:
        new_ai_msg = AIMessage(
            content=last_message.content or "",
            tool_calls=new_tool_calls,
        )
        new_messages.append(new_ai_msg)
        new_messages.extend(review_messages)
        return {
            "messages": new_messages,
            "iterations": state.get("iterations", 0) + 1,
            "sql_review_count": state.get("sql_review_count", 0) + 1,
        }

    return {
        "iterations": state.get("iterations", 0) + 1,
        "sql_review_count": state.get("sql_review_count", 0) + 1,
    }


def should_continue(state: AgentState) -> str:
    if state.get("iterations", 0) >= config.MAX_ITERATIONS:
        return "end"
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        tool_names = [tc["name"] for tc in last.tool_calls]
        if "execute_sql" in tool_names and state.get("sql_review_count", 0) < config.MAX_SQL_REVIEW_ATTEMPTS:
            return "review"
        return "tools"
    return "end"