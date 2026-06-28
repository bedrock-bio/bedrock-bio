import json

import pytest

from bedrock_bio.config import config
from bedrock_bio.list_tables import list_tables
from conftest import requires_live_v2_manifest


def _local_manifest(monkeypatch, tmp_path):
    """Point the config at a hand-built two-namespace v2 manifest on disk."""
    manifest = {
        "version": 2,
        "published_at": "2026-06-27T00:00:00Z",
        "namespaces": {
            "ns_a": {
                "name": "Namespace A",
                "license": "CC0 1.0",
                "citation": "Author. Journal 2025. doi:10.0/a",
                "context": "What ns_a is.",
                "tables": {
                    "tbl_one": {
                        "partitions": {},
                        "iceberg_json": "s3://test/a1.json",
                        "columns": [],
                        "context": "",
                    },
                    "tbl_two": {
                        "partitions": {},
                        "iceberg_json": "s3://test/a2.json",
                        "columns": [],
                        "context": "",
                    },
                },
            },
            "ns_b": {
                "name": "Namespace B",
                "license": "CC0 1.0",
                "citation": "Author. Journal 2025. doi:10.0/b",
                "context": "What ns_b is.",
                "tables": {
                    "tbl_three": {
                        "partitions": {},
                        "iceberg_json": "s3://test/b1.json",
                        "columns": [],
                        "context": "",
                    },
                },
            },
        },
    }
    fixture = tmp_path / "manifest.json"
    fixture.write_text(json.dumps(manifest))
    monkeypatch.setattr(
        type(config), "manifest_url", property(lambda self: f"file://{fixture}")
    )


class TestListTables:
    def test_returns_list_of_strings(self):
        requires_live_v2_manifest()
        result = list_tables()
        assert isinstance(result, list)
        for name in result:
            assert isinstance(name, str)
        assert "dbsnp.vcf" in result

    def test_no_namespace_returns_all_tables(self, monkeypatch, tmp_path):
        _local_manifest(monkeypatch, tmp_path)
        result = list_tables()
        assert set(result) == {"ns_a.tbl_one", "ns_a.tbl_two", "ns_b.tbl_three"}

    def test_namespace_filters_to_that_namespace(self, monkeypatch, tmp_path):
        _local_manifest(monkeypatch, tmp_path)
        result = list_tables("ns_a")
        assert result == ["ns_a.tbl_one", "ns_a.tbl_two"]

    def test_unknown_namespace_raises(self, monkeypatch, tmp_path):
        _local_manifest(monkeypatch, tmp_path)
        with pytest.raises(ValueError, match="not found"):
            list_tables("not_a_namespace")
