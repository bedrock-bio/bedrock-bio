import pytest

from bedrock_bio.describe_namespace import describe_namespace


class TestDescribeNamespace:
    def test_no_namespace(self):
        with pytest.raises(ValueError, match="not found"):
            describe_namespace("not_a_namespace")

    def test_returns_expected_keys(self):
        result = describe_namespace("dbsnp")
        assert result["id"] == "dbsnp"
        assert isinstance(result["name"], str)
        assert len(result["name"]) > 0
        assert isinstance(result["description"], str)
        assert isinstance(result["source_url"], str)
        assert isinstance(result["license"], str)
        assert isinstance(result["instructions"], str)
        assert isinstance(result["citation"], dict)

    def test_tables_field_is_list_of_fqns(self):
        result = describe_namespace("dbsnp")
        assert isinstance(result["tables"], list)
        assert len(result["tables"]) > 0
        for fqn in result["tables"]:
            assert fqn.startswith("dbsnp.")
        assert "dbsnp.vcf" in result["tables"]

    def test_tables_list_agrees_with_list_tables_filtered(self):
        from bedrock_bio.list_tables import list_tables

        result = describe_namespace("dbsnp")
        from_list = [t for t in list_tables() if t.startswith("dbsnp.")]
        assert set(result["tables"]) == set(from_list)
