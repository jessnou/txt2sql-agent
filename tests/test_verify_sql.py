from __future__ import annotations

from unittest.mock import MagicMock

from txt2sql_agent.schema_repository import SchemaRepository


class TestVerifySql:
    def test_explain_success(self, mock_ch_client):
        repo = SchemaRepository(mock_ch_client)
        ok, err = repo.verify_sql("SELECT 1")
        assert ok is True
        assert err == ""

    def test_explain_syntax_error(self, mock_ch_client):
        from clickhouse_connect.driver.exceptions import DatabaseError
        mock_ch_client.query.side_effect = DatabaseError("Syntax error: missing comma")
        repo = SchemaRepository(mock_ch_client)
        ok, err = repo.verify_sql("SELECT FROM")
        assert ok is False
        assert "Syntax error" in err or "error" in err.lower()

    def test_explain_missing_table(self, mock_ch_client):
        from clickhouse_connect.driver.exceptions import DatabaseError
        mock_ch_client.query.side_effect = DatabaseError("Table nonexistent_table doesn't exist")
        repo = SchemaRepository(mock_ch_client)
        ok, err = repo.verify_sql("SELECT * FROM nonexistent_table")
        assert ok is False
        assert "doesn't exist" in err or "not exist" in err.lower()

    def test_explain_timeout(self, mock_ch_client):
        mock_ch_client.query.side_effect = TimeoutError("Query timed out")
        repo = SchemaRepository(mock_ch_client)
        ok, err = repo.verify_sql("SELECT * FROM metrics_facts")
        assert ok is False
        assert err != ""