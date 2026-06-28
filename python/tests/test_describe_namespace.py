import pytest

from bedrock_bio.describe_namespace import describe_namespace
from bedrock_bio.list_tables import list_tables


class TestDescribeNamespace:
    def test_errors_on_unknown_namespace(self, v2_manifest):
        with pytest.raises(ValueError, match="not found"):
            describe_namespace("not_a_namespace")

    def test_returns_expected_fields(self, v2_manifest):
        result = describe_namespace("test_ns")
        assert result["name"] == "Test Namespace"
        assert isinstance(result["license"], str)
        assert isinstance(result["citation"], str)
        assert isinstance(result["context"], str)

    def test_tables_field_is_list_of_fqns(self, v2_manifest):
        result = describe_namespace("test_ns")
        assert len(result["tables"]) > 0
        assert all(fqn.startswith("test_ns.") for fqn in result["tables"])
        assert "test_ns.test_tbl" in result["tables"]

    def test_tables_agree_with_list_tables_filtered(self, v2_manifest):
        result = describe_namespace("test_ns")
        from_list = [t for t in list_tables() if t.startswith("test_ns.")]
        assert set(result["tables"]) == set(from_list)
