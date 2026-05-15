from __future__ import annotations

import uuid

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich.console import Console
from rich.panel import Panel

from . import config
from .graph import build_graph


def _init_langfuse():
    if not config.LANGFUSE_ENABLED or not config.LANGFUSE_PUBLIC_KEY:
        return None
    try:
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        Langfuse(
            public_key=config.LANGFUSE_PUBLIC_KEY,
            secret_key=config.LANGFUSE_SECRET_KEY,
            host=config.LANGFUSE_BASE_URL,
        )
        return CallbackHandler()
    except Exception:
        return None


def main() -> None:
    load_dotenv()

    console = Console()

    if not config.OPENAI_API_KEY:
        console.print("[red]Error: OPENAI_API_KEY not set. Create a .env file based on .env.example[/red]")
        raise SystemExit(1)

    console.print(Panel(
        "[bold]txt2sql-agent[/bold]\nReAct agent with ClickHouse exploration tools",
        subtitle=f"Model: {config.OPENAI_MODEL} | CH: {config.CLICKHOUSE_HOST}:{config.CLICKHOUSE_PORT}/{config.CLICKHOUSE_DB}",
    ))
    console.print("[dim]Type your question in Russian or English. Press Ctrl+C to exit.[/dim]\n")

    agent = build_graph()
    langfuse_handler = _init_langfuse()
    session_id = str(uuid.uuid4()) if langfuse_handler else None

    if langfuse_handler:
        console.print(f"[dim]Langfuse tracing enabled (session: {session_id[:8]}...)[/dim]\n")

    try:
        while True:
            try:
                query = console.input("[bold green]You:[/bold green] ")
            except EOFError:
                break
            if query.strip().lower() in ("exit", "quit", "q"):
                break
            if not query.strip():
                continue

            run_config = None
            if langfuse_handler:
                metadata = {
                    "langfuse_session_id": session_id,
                    "langfuse_tags": ["txt2sql-agent"],
                }
                run_config = {"callbacks": [langfuse_handler], "metadata": metadata}

            input_state = {
                "messages": [HumanMessage(content=query)],
                "iterations": 0,
            }

            with console.status("[dim]Thinking...[/dim]"):
                for event in agent.stream(input_state, config=run_config):
                    for node_name, node_output in event.items():
                        if node_name == "agent":
                            msg = node_output.get("messages", [])[-1] if node_output.get("messages") else None
                            if msg and isinstance(msg, AIMessage):
                                if msg.tool_calls:
                                    if msg.content:
                                        console.print(Panel(
                                            msg.content,
                                            title="[dim]Thought[/dim]",
                                            border_style="dim",
                                        ))
                                    for tc in msg.tool_calls:
                                        args_str = ", ".join(f"{k}={v!r}" for k, v in tc["args"].items())
                                        console.print(f"[yellow]→ {tc['name']}({args_str})[/yellow]")
                                else:
                                    if msg.content:
                                        console.print(Panel(
                                            msg.content,
                                            title="Answer",
                                            border_style="cyan",
                                        ))
                        elif node_name == "tools":
                            msgs = node_output.get("messages", [])
                            for msg in msgs:
                                if isinstance(msg, ToolMessage):
                                    content = msg.content
                                    if len(content) > 500:
                                        content = content[:500] + "..."
                                    if content.startswith("SQL Error:"):
                                        console.print(Panel(
                                            content,
                                            title="[red]Error[/red]",
                                            border_style="red",
                                        ))
                                    else:
                                        console.print(Panel(
                                            content,
                                            title="[green]Observation[/green]",
                                            border_style="green",
                                        ))

            console.print()
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")
    finally:
        if langfuse_handler:
            from langfuse import get_client
            get_client().shutdown()


if __name__ == "__main__":
    main()