import duckdb
import pytest

from bedrock_bio.config import config
from conftest import local_manifest


class TestManifest:
    def test_returns_dict_with_expected_structure(self, v2_manifest):
        result = config.get_manifest()
        assert isinstance(result, dict)
        assert len(result) > 0
        for key, entry in result.items():
            assert isinstance(key, str)
            assert isinstance(entry["iceberg_json"], str)
            assert isinstance(entry["partitions"], dict)
            assert isinstance(entry["columns"], list)
            assert isinstance(entry["context"], str)

    def test_caches_result(self, v2_manifest):
        assert config.get_manifest() is config.get_manifest()

    def test_errors_when_url_unreachable(self, monkeypatch):
        monkeypatch.setattr(
            type(config),
            "manifest_url",
            property(lambda self: "https://invalid.invalid/manifest.json"),
        )
        with pytest.raises(ConnectionError, match="Unable to access manifest URL"):
            config.get_manifest()

    def test_rejects_unsupported_version(self, monkeypatch, tmp_path):
        local_manifest({"version": 1, "namespaces": {}}, monkeypatch, tmp_path)
        with pytest.raises(ValueError, match="Unsupported manifest version"):
            config.get_manifest()

    def test_lifts_v2_table_block(self, v2_manifest):
        entry = config.get_manifest()["test_ns.test_tbl"]
        assert entry["iceberg_json"] == "s3://test/metadata.json"
        assert entry["context"] == "What this table is and how to query it."
        assert entry["partitions"]["release"]["default"] == "26.03.0"
        assert entry["partitions"]["release"]["values"] == ["26.03.0", "26.02.0"]
        assert entry["partitions"]["chromosome"]["default"] == ""

        cols = entry["columns"]
        assert cols[0] == {
            "name": "disease_id",
            "type": "TEXT",
            "description": "An identifier.",
            "nullable": False,
        }
        assert all("allowed_values" not in col for col in cols)

    def test_lifts_v2_namespace_block(self, v2_manifest):
        ns = config.get_namespaces()["test_ns"]
        assert ns["name"] == "Test Namespace"
        assert ns["license"] == "CC0 1.0"
        assert ns["citation"] == "Some Author. Some Journal 2025. doi:10.0/test"
        assert ns["context"] == "What this data source is and how to use it."
        assert ns["tables"] == ["test_ns.test_tbl"]

    def test_namespaces_have_expected_structure(self, v2_manifest):
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


class TestConnection:
    def test_uses_anonymous_vhost(self):
        conn = config.get_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        assert conn.sql("FROM duckdb_secrets()").fetchall() == []
        endpoint = conn.sql("SELECT current_setting('s3_endpoint')").fetchone()[0]
        assert endpoint == "bedrock.bio"
        url_style = conn.sql("SELECT current_setting('s3_url_style')").fetchone()[0]
        assert url_style == "vhost"

    def test_caches(self):
        assert config.get_connection() is config.get_connection()
