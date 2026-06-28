import json

import pytest

from bedrock_bio.config import config
from bedrock_bio.describe_table import describe_table
from conftest import requires_live_v2_manifest


class TestDescribeTable:
    def test_no_table(self):
        requires_live_v2_manifest()
        with pytest.raises(ValueError, match="not found in manifest"):
            describe_table("not_a_table")

    def test_returns_expected_keys(self):
        requires_live_v2_manifest()
        result = describe_table("dbsnp.vcf")
        assert result["name"] == "dbsnp.vcf"
        assert isinstance(result["context"], str)
        assert len(result["context"]) > 0
        assert isinstance(result["columns"], list)
        assert len(result["columns"]) > 0
        assert isinstance(result["partitions"], dict)

    def test_columns_have_expected_fields(self):
        requires_live_v2_manifest()
        result = describe_table("dbsnp.vcf")
        for col in result["columns"]:
            assert "name" in col
            assert "type" in col
            assert "description" in col
            assert "nullable" in col
            # v2 columns carry no allowed_values.
            assert "allowed_values" not in col

    def test_partitioned_table_returns_partition_block(self):
        requires_live_v2_manifest()
        result = describe_table("dbsnp.vcf")
        # dbsnp.vcf is hive-partitioned; partition columns appear as keys, each
        # with values + default.
        partitions = result["partitions"]
        assert "assembly" in partitions
        assert "chromosome" in partitions
        for col in partitions.values():
            assert "values" in col
            assert "default" in col

    def test_unpartitioned_table_returns_empty_partitions(self, monkeypatch, tmp_path):
        # The other table shape: a single-file table with no partition columns.
        # Pinned to a fixture rather than live data -- every table in the live
        # prod manifest is currently partitioned (ensembl.* by release), so the
        # unpartitioned shape can only be exercised deterministically.
        manifest = {
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
        fixture = tmp_path / "manifest.json"
        fixture.write_text(json.dumps(manifest))
        monkeypatch.setattr(
            type(config), "manifest_url", property(lambda self: f"file://{fixture}")
        )
        result = describe_table("test_ns.flat_tbl")
        assert result["partitions"] == {}
