import pytest

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

    def test_unpartitioned_table_returns_empty_partitions(self):
        # The other table shape: a single-file table with no partition columns
        # (dbsnp.vcf above is hive-partitioned).
        requires_live_v2_manifest()
        result = describe_table("ensembl.taxonomies")
        assert result["partitions"] == {}
