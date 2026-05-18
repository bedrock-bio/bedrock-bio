import pytest

from bedrock_bio.describe_table import describe_table


class TestDescribeTable:
    def test_no_table(self):
        with pytest.raises(ValueError, match="not found in catalog"):
            describe_table("not_a_table")

    def test_returns_expected_keys(self):
        result = describe_table("ukb_ppp.pqtls")
        assert result["name"] == "ukb_ppp.pqtls"
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

    def test_unpartitioned_table_returns_empty_partition_by(self):
        result = describe_table("open_targets.targets")
        assert result["partition_by"] == []
        assert len(result["sort_by"]) > 0

    def test_partitioned_table_returns_expected_partition_and_sort_columns(self):
        result = describe_table("dbsnp.vcf")
        assert result["partition_by"] == ["assembly", "chromosome"]
        assert result["sort_by"] == ["position"]
