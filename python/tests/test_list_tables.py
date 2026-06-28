import pytest

from bedrock_bio.list_tables import list_tables
from conftest import local_manifest, requires_live_v2_manifest

TWO_NS_MANIFEST = {
    "version": 2,
    "namespaces": {
        "ns_a": {
            "tables": {
                "tbl_one": {"iceberg_json": "s3://test/a1.json"},
                "tbl_two": {"iceberg_json": "s3://test/a2.json"},
            }
        },
        "ns_b": {"tables": {"tbl_three": {"iceberg_json": "s3://test/b1.json"}}},
    },
}


class TestListTables:
    def test_returns_list_of_strings(self):
        requires_live_v2_manifest()
        result = list_tables()
        assert isinstance(result, list)
        assert all(isinstance(name, str) for name in result)
        assert "dbsnp.vcf" in result

    def test_no_namespace_returns_all_tables(self, monkeypatch, tmp_path):
        local_manifest(TWO_NS_MANIFEST, monkeypatch, tmp_path)
        assert set(list_tables()) == {"ns_a.tbl_one", "ns_a.tbl_two", "ns_b.tbl_three"}

    def test_namespace_filters_to_that_namespace(self, monkeypatch, tmp_path):
        local_manifest(TWO_NS_MANIFEST, monkeypatch, tmp_path)
        assert list_tables("ns_a") == ["ns_a.tbl_one", "ns_a.tbl_two"]

    def test_unknown_namespace_raises(self, monkeypatch, tmp_path):
        local_manifest(TWO_NS_MANIFEST, monkeypatch, tmp_path)
        with pytest.raises(ValueError, match="not found"):
            list_tables("not_a_namespace")
