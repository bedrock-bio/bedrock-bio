import json

import duckdb
import pytest

from bedrock_bio.config import config


class TestConfig:
    def test_manifest_returns_dict_with_expected_structure(self):
        result = config.get_manifest()
        assert isinstance(result, dict)
        assert len(result) > 0
        for key, entry in result.items():
            assert isinstance(key, str)
            assert isinstance(entry, dict)
            assert isinstance(entry["metadata_json"], str)
            assert isinstance(entry["partition_by"], list)
            assert isinstance(entry["sort_by"], list)
            assert isinstance(entry["columns"], list)

    def test_manifest_caches_result(self):
        first = config.get_manifest()
        second = config.get_manifest()
        assert first is second

    def test_manifest_errors_when_url_unreachable(self, monkeypatch):
        monkeypatch.setattr(
            type(config),
            "manifest_url",
            property(lambda self: "https://invalid.invalid/manifest.json"),
        )
        with pytest.raises(ConnectionError, match="Unable to access manifest URL"):
            config.get_manifest()

    def test_manifest_preserves_whitelisted_column_keys(self, monkeypatch, tmp_path):
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
        monkeypatch.setattr(
            type(config), "manifest_url", property(lambda self: f"file://{fixture}")
        )

        result = config.get_manifest()
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

    def test_namespaces_returns_dict_with_expected_structure(self):
        result = config.get_namespaces()
        assert isinstance(result, dict)
        assert len(result) > 0
        for ns_id, entry in result.items():
            assert entry["id"] == ns_id
            assert isinstance(entry["name"], str)
            assert isinstance(entry["description"], str)
            assert isinstance(entry["tables"], list)
            assert all(fqn.startswith(f"{ns_id}.") for fqn in entry["tables"])

    def test_connection_uses_anonymous_vhost(self):
        conn = config.get_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        # No secret — reads are anonymous over the public custom domain.
        assert conn.sql("FROM duckdb_secrets()").fetchall() == []
        endpoint = conn.sql("SELECT current_setting('s3_endpoint')").fetchone()[0]
        assert endpoint == "bedrock.bio"
        url_style = conn.sql("SELECT current_setting('s3_url_style')").fetchone()[0]
        assert url_style == "vhost"

    def test_connection_caches(self):
        first = config.get_connection()
        second = config.get_connection()
        assert first is second
