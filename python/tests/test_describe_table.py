import pytest

from bedrock_bio.describe_table import describe_table
from conftest import local_manifest

FLAT_MANIFEST = {
    "version": 2,
    "published_at": "2026-06-27T00:00:00Z",
    "namespaces": {
        "test_ns": {
            "name": "Test Namespace",
            "license": "CC0 1.0",
            "citation": "Some Author. Some Journal 2025. doi:10.0/test",
            "context": "What this data source is.",
            "tables": {
                "flat_tbl": {
                    "partitions": {},
                    "iceberg_json": "s3://test/metadata.json",
                    "columns": [
                        {
                            "name": "id",
                            "type": "TEXT",
                            "description": "An identifier.",
                            "nullable": False,
                        }
                    ],
                    "context": "A single-file table with no partitions.",
                }
            },
        }
    },
}


class TestDescribeTable:
    def test_errors_on_unknown_table(self, v2_manifest):
        with pytest.raises(ValueError, match="not found in manifest"):
            describe_table("not_a_table")

    def test_returns_expected_fields(self, v2_manifest):
        result = describe_table("test_ns.test_tbl")
        assert result["name"] == "test_ns.test_tbl"
        assert len(result["context"]) > 0
        assert len(result["columns"]) > 0
        assert isinstance(result["partitions"], dict)

    def test_columns_have_expected_fields(self, v2_manifest):
        for col in describe_table("test_ns.test_tbl")["columns"]:
            assert {"name", "type", "description", "nullable"} <= col.keys()
            assert "allowed_values" not in col

    def test_partitioned_table_returns_partition_block(self, v2_manifest):
        partitions = describe_table("test_ns.test_tbl")["partitions"]
        assert "release" in partitions
        assert "chromosome" in partitions
        for col in partitions.values():
            assert {"values", "default"} <= col.keys()

    def test_unpartitioned_table_returns_empty_partitions(self, monkeypatch, tmp_path):
        local_manifest(FLAT_MANIFEST, monkeypatch, tmp_path)
        assert describe_table("test_ns.flat_tbl")["partitions"] == {}
