import json

import duckdb
import pytest

from bedrock_bio.config import config


class TestConfig:
    def test_catalog_returns_dict_with_expected_structure(self):
        result = config.get_catalog()
        assert isinstance(result, dict)
        assert len(result) > 0
        for key, entry in result.items():
            assert isinstance(key, str)
            assert isinstance(entry, dict)
            assert isinstance(entry["metadata_json"], str)
            assert isinstance(entry["partition_by"], list)
            assert isinstance(entry["sort_by"], list)
            assert isinstance(entry["columns"], list)

    def test_catalog_caches_result(self):
        first = config.get_catalog()
        second = config.get_catalog()
        assert first is second

    def test_catalog_errors_when_url_unreachable(self, monkeypatch):
        monkeypatch.setattr(
            "bedrock_bio.config.CATALOG_URL",
            "https://invalid.invalid/manifest.json",
        )
        with pytest.raises(ConnectionError, match="Unable to access manifest URL"):
            config.get_catalog()

    def test_catalog_preserves_whitelisted_column_keys(self, monkeypatch, tmp_path):
        fixture = tmp_path / "manifest.json"
        fixture.write_text(
            json.dumps(
                {
                    "namespaces": {
                        "test_ns": {
                            "citation": {},
                            "source_url": "https://example.com",
                            "license": "MIT",
                            "tables": {
                                "test_tbl": {
                                    "metadata_json": "s3://test/metadata.json",
                                    "description": "test",
                                    "partition_by": [],
                                    "sort_by": [],
                                    "columns": [
                                        {
                                            "name": "col_with_extras",
                                            "type": "string",
                                            "description": "desc",
                                            "nullable": True,
                                            "allowed_values": ["A", "B"],
                                            "extra_field": "should_be_stripped",
                                            "another_extra": 123,
                                        },
                                        {
                                            "name": "col_minimal",
                                            "type": "int",
                                            "description": "minimal",
                                        },
                                    ],
                                }
                            },
                        }
                    }
                }
            )
        )
        monkeypatch.setattr("bedrock_bio.config.CATALOG_URL", f"file://{fixture}")

        result = config.get_catalog()
        cols = result["test_ns.test_tbl"]["columns"]

        c1 = cols[0]
        assert c1["name"] == "col_with_extras"
        assert c1["type"] == "string"
        assert c1["description"] == "desc"
        assert c1["nullable"] is True
        assert c1["allowed_values"] == ["A", "B"]
        assert "extra_field" not in c1
        assert "another_extra" not in c1

        c2 = cols[1]
        assert c2["name"] == "col_minimal"
        assert "nullable" not in c2
        assert "allowed_values" not in c2

    def test_credentials_returns_expected_keys(self):
        result = config.get_credentials()
        expected_keys = {
            "BB_R2_ACCOUNT_ID",
            "BB_R2_ACCESS_KEY_ID",
            "BB_R2_SECRET_ACCESS_KEY",
        }
        assert set(result.keys()) == expected_keys
        for value in result.values():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_credentials_caches_result(self):
        first = config.get_credentials()
        second = config.get_credentials()
        assert first is second

    def test_credentials_errors_when_url_unreachable(self, monkeypatch):
        monkeypatch.setattr(
            "bedrock_bio.config.CREDENTIALS_URL",
            "https://invalid.invalid/credentials.json",
        )
        with pytest.raises(ConnectionError, match="Unable to fetch credentials"):
            config.get_credentials()

    def test_connection_returns_duckdb_with_s3_secret(self):
        conn = config.get_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        rows = conn.sql("FROM duckdb_secrets()").fetchall()
        assert len(rows) == 1
        assert "s3" in str(rows[0])
        assert "r2.cloudflarestorage.com" in rows[0][-1]

    def test_connection_caches(self):
        first = config.get_connection()
        second = config.get_connection()
        assert first is second

    def test_reset_clears_cached_state(self):
        config.get_catalog()
        config.get_credentials()
        config.get_connection()
        assert config.catalog is not None
        assert config.credentials is not None
        assert config.conn is not None
        config.reset()
        assert config.catalog is None
        assert config.credentials is None
        assert config.conn is None
