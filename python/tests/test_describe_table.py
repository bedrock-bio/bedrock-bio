import pytest

from bedrock_bio.describe_table import describe_table


class TestDescribeTable:
    def test_no_table(self):
        with pytest.raises(ValueError, match="not found in manifest"):
            describe_table("not_a_table")

    def test_returns_expected_keys(self):
        result = describe_table("dbsnp.vcf")
        assert result["name"] == "dbsnp.vcf"
        assert isinstance(result["description"], str)
        assert len(result["description"]) > 0
        assert isinstance(result["citation"], dict)
        assert isinstance(result["source_url"], str)
        assert isinstance(result["license"], str)
        assert isinstance(result["columns"], list)
        assert len(result["columns"]) > 0

    def test_columns_have_expected_fields(self):
        result = describe_table("dbsnp.vcf")
        for col in result["columns"]:
            assert "name" in col
            assert "type" in col
            assert "description" in col

    def test_partitioned_table_returns_expected_partition_and_sort_columns(self):
        result = describe_table("dbsnp.vcf")
        assert result["partition_by"] == ["assembly", "chromosome"]
        assert result["sort_by"] == ["position"]

    def test_unpartitioned_table_returns_empty_partition_by(self):
        # The other table shape: a single-file table with no partition columns
        # (dbsnp.vcf above is hive-partitioned).
        result = describe_table("ensembl.taxonomies")
        assert result["partition_by"] == []
        assert len(result["sort_by"]) > 0
