import json

import duckdb
import pytest

from bedrock_bio.config import config


# A hand-built v2 manifest derived from docs/MANIFEST.md, used to unit-test the
# parser without a live network fetch.
V2_MANIFEST = {
    "version": 2,
    "published_at": "2026-06-27T00:00:00Z",
    "namespaces": {
        "test_ns": {
            "name": "Test Namespace",
            "license": "CC0 1.0",
            "citation": "Some Author. Some Journal 2025. doi:10.0/test",
            "context": "What this data source is and how to use it.",
            "tables": {
                "test_tbl": {
                    "partitions": {
                        "release": {
                            "values": ["26.03.0", "26.02.0"],
                            "default": "26.03.0",
                        },
                        "chromosome": {"values": ["1", "22"], "default": ""},
                    },
                    "iceberg_json": "s3://test/metadata.json",
                    "columns": [
                        {
                            "name": "disease_id",
                            "type": "TEXT",
                            "description": "An identifier.",
                            "nullable": False,
                        },
                        {
                            "name": "score",
                            "type": "DOUBLE",
                            "description": "A score.",
                            "nullable": True,
                        },
                    ],
                    "context": "What this table is and how to query it.",
                }
            },
        }
    },
}


@pytest.fixture
def v2_manifest(monkeypatch, tmp_path):
    """Point the config at a hand-built v2 manifest fixture on disk."""
    fixture = tmp_path / "manifest.json"
    fixture.write_text(json.dumps(V2_MANIFEST))
    monkeypatch.setattr(
        type(config), "manifest_url", property(lambda self: f"file://{fixture}")
    )


class TestConfig:
    def test_manifest_returns_dict_with_expected_structure(self, v2_manifest):
        result = config.get_manifest()
        assert isinstance(result, dict)
        assert len(result) > 0
        for key, entry in result.items():
            assert isinstance(key, str)
            assert isinstance(entry, dict)
            assert isinstance(entry["iceberg_json"], str)
            assert isinstance(entry["partitions"], dict)
            assert isinstance(entry["columns"], list)
            assert isinstance(entry["context"], str)

    def test_manifest_caches_result(self, v2_manifest):
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

    def test_manifest_rejects_unsupported_version(self, monkeypatch, tmp_path):
        fixture = tmp_path / "manifest.json"
        fixture.write_text(json.dumps({"version": 1, "namespaces": {}}))
        monkeypatch.setattr(
            type(config), "manifest_url", property(lambda self: f"file://{fixture}")
        )
        with pytest.raises(ValueError, match="Unsupported manifest version"):
            config.get_manifest()

    def test_manifest_lifts_v2_table_block(self, v2_manifest):
        result = config.get_manifest()
        entry = result["test_ns.test_tbl"]

        assert entry["iceberg_json"] == "s3://test/metadata.json"
        assert entry["context"] == "What this table is and how to query it."
        assert entry["partitions"]["release"]["default"] == "26.03.0"
        assert entry["partitions"]["release"]["values"] == ["26.03.0", "26.02.0"]
        assert entry["partitions"]["chromosome"]["default"] == ""

        # Columns are lifted wholesale (no cherry-pick), and carry no
        # allowed_values in v2.
        cols = entry["columns"]
        assert cols[0] == {
            "name": "disease_id",
            "type": "TEXT",
            "description": "An identifier.",
            "nullable": False,
        }
        assert all("allowed_values" not in col for col in cols)

    def test_manifest_lifts_v2_namespace_block(self, v2_manifest):
        ns = config.get_namespaces()["test_ns"]
        assert ns["name"] == "Test Namespace"
        assert ns["license"] == "CC0 1.0"
        assert ns["citation"] == "Some Author. Some Journal 2025. doi:10.0/test"
        assert ns["context"] == "What this data source is and how to use it."
        assert ns["tables"] == ["test_ns.test_tbl"]
        # citation is a pre-formatted string in v2, not a structured object.
        assert isinstance(ns["citation"], str)

    def test_namespaces_returns_dict_with_expected_structure(self, v2_manifest):
        result = config.get_namespaces()
        assert isinstance(result, dict)
        assert len(result) > 0
        for ns_id, entry in result.items():
            assert isinstance(entry["name"], str)
            assert isinstance(entry["citation"], str)
            assert isinstance(entry["license"], str)
            assert isinstance(entry["context"], str)
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
