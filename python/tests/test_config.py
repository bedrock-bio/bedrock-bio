import duckdb

from bedrock_bio.config import config


class TestConfig:
    def test_catalog_returns_dict_with_expected_structure(self):
        result = config.get_catalog()
        assert isinstance(result, dict)
        assert len(result) > 0
        for key, entry in result.items():
            assert isinstance(key, str)
            assert isinstance(entry, dict)
            assert isinstance(entry["metadata_json"], str)
            assert isinstance(entry["partition_by"], list)
            assert isinstance(entry["sort_by"], list)
            assert isinstance(entry["columns"], list)

    def test_catalog_caches_result(self):
        first = config.get_catalog()
        second = config.get_catalog()
        assert first is second

    def test_credentials_returns_expected_keys(self):
        result = config.get_credentials()
        expected_keys = {
            "BB_R2_ACCOUNT_ID",
            "BB_R2_ACCESS_KEY_ID",
            "BB_R2_SECRET_ACCESS_KEY",
        }
        assert set(result.keys()) == expected_keys
        for value in result.values():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_credentials_caches_result(self):
        first = config.get_credentials()
        second = config.get_credentials()
        assert first is second

    def test_connection_returns_duckdb_with_s3_secret(self):
        conn = config.get_connection()
        assert isinstance(conn, duckdb.DuckDBPyConnection)
        rows = conn.sql("FROM duckdb_secrets()").fetchall()
        assert len(rows) == 1
        assert "s3" in str(rows[0])
        assert "r2.cloudflarestorage.com" in rows[0][-1]

    def test_connection_caches(self):
        first = config.get_connection()
        second = config.get_connection()
        assert first is second
