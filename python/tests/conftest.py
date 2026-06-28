import json

import pytest

from bedrock_bio.config import config

V2_MANIFEST = {
    "version": 2,
    "published_at": "2026-06-27T00:00:00Z",
    "namespaces": {
        "test_ns": {
            "name": "Test Namespace",
            "license": "CC0 1.0",
            "citation": "Some Author. Some Journal 2025. doi:10.0/test",
            "context": "What this data source is and how to use it.",
            "tables": {
                "test_tbl": {
                    "partitions": {
                        "release": {
                            "values": ["26.03.0", "26.02.0"],
                            "default": "26.03.0",
                        },
                        "chromosome": {"values": ["1", "22"], "default": ""},
                    },
                    "iceberg_json": "s3://test/metadata.json",
                    "columns": [
                        {
                            "name": "disease_id",
                            "type": "TEXT",
                            "description": "An identifier.",
                            "nullable": False,
                        },
                        {
                            "name": "score",
                            "type": "DOUBLE",
                            "description": "A score.",
                            "nullable": True,
                        },
                    ],
                    "context": "What this table is and how to query it.",
                }
            },
        }
    },
}


@pytest.fixture(autouse=True)
def clear_state():
    yield
    if config.conn is not None:
        config.conn.close()
    config.manifest = None
    config.namespaces = None
    config.conn = None


def local_manifest(manifest, monkeypatch, tmp_path):
    """Point the config at a manifest fixture on disk for one test."""
    fixture = tmp_path / "manifest.json"
    fixture.write_text(json.dumps(manifest))
    monkeypatch.setattr(
        type(config), "manifest_url", property(lambda self: f"file://{fixture}")
    )


@pytest.fixture
def v2_manifest(monkeypatch, tmp_path):
    local_manifest(V2_MANIFEST, monkeypatch, tmp_path)


def requires_live_v2_manifest():
    """Skip a test when the live manifest can't be fetched or isn't v2 yet.

    The v2 manifest is published by a separate Dagster job; until it runs the
    live manifest is still v1 and the version gate raises.
    """
    try:
        config.get_manifest()
    except Exception as exc:
        pytest.skip(f"live v2 manifest unavailable: {exc}")
