from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://polza.ai/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "txt2sql")
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "3"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "http://localhost:3000"))
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() in ("true", "1", "yes")

_SCHEMA_OVERRIDES: dict | None = None


def get_schema_overrides() -> dict:
    global _SCHEMA_OVERRIDES
    if _SCHEMA_OVERRIDES is not None:
        return _SCHEMA_OVERRIDES

    overrides_path = Path(__file__).resolve().parent.parent.parent / "config" / "schema_overrides.yaml"
    if overrides_path.exists():
        with open(overrides_path) as f:
            _SCHEMA_OVERRIDES = yaml.safe_load(f) or {}
    else:
        _SCHEMA_OVERRIDES = {}

    return _SCHEMA_OVERRIDES


def get_glossary() -> str:
    overrides = get_schema_overrides()
    glossary = overrides.get("glossary", {})
    if not glossary:
        return ""
    lines = [f"  {term}: {meaning}" for term, meaning in glossary.items()]
    return "\n".join(lines)


def get_business_context() -> str:
    overrides = get_schema_overrides()
    return overrides.get("business_context", "")