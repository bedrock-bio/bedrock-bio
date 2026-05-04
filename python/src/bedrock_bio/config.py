import duckdb
import json
import os
import urllib.request
from dataclasses import dataclass

CATALOG_URL = "https://data.bedrock.bio/catalog.json"
CREDENTIALS_URL = "https://data.bedrock.bio/credentials.json"


@dataclass
class Config:
    catalog: dict[str, dict] | None = None
    credentials: dict[str, str] | None = None
    conn: duckdb.DuckDBPyConnection | None = None

    def get_catalog(self) -> dict[str, dict]:
        if self.catalog is not None:
            return self.catalog

        try:
            request = urllib.request.Request(
                CATALOG_URL, headers={"User-Agent": "bedrock-bio"}
            )
            with urllib.request.urlopen(request) as response:
                raw = json.loads(response.read())
        except Exception:
            raise ConnectionError(
                f"Unable to access catalog URL '{CATALOG_URL}'. "
                "Check internet connection and try again."
            )

        self.catalog = {}
        for ns, ns_data in raw["namespaces"].items():
            for table, meta in ns_data["tables"].items():
                columns = [
                    {
                        k: col[k]
                        for k in (
                            "name",
                            "type",
                            "description",
                            "nullable",
                            "allowed_values",
                        )
                        if k in col
                    }
                    for col in meta.get("columns", [])
                ]

                self.catalog[f"{ns}.{table}"] = {
                    "metadata_json": meta["metadata_json"],
                    "partition_by": list(meta.get("partition_by", [])),
                    "sort_by": list(meta.get("sort_by", [])),
                    "description": meta.get("description", ""),
                    "citation": ns_data.get("citation"),
                    "source_url": ns_data.get("source_url", ""),
                    "license": ns_data.get("license", ""),
                    "columns": columns,
                }
        return self.catalog

    def get_credentials(self) -> dict[str, str]:
        if self.credentials is not None:
            return self.credentials

        override_credentials = {
            "BB_R2_ACCOUNT_ID": os.environ.get("BB_R2_ACCOUNT_ID", ""),
            "BB_R2_ACCESS_KEY_ID": os.environ.get("BB_R2_ACCESS_KEY_ID", ""),
            "BB_R2_SECRET_ACCESS_KEY": os.environ.get("BB_R2_SECRET_ACCESS_KEY", ""),
        }

        if all(override_credentials.values()):
            self.credentials = override_credentials
        else:
            try:
                request = urllib.request.Request(
                    CREDENTIALS_URL, headers={"User-Agent": "bedrock-bio"}
                )
                with urllib.request.urlopen(request) as response:
                    self.credentials = json.loads(response.read())
            except Exception:
                raise ConnectionError(
                    f"Unable to fetch credentials from '{CREDENTIALS_URL}'. "
                    "Check internet connection and try again."
                )
        return self.credentials

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        if self.conn is not None:
            return self.conn

        credentials = self.get_credentials()
        self.conn = duckdb.connect()
        self.conn.sql("INSTALL httpfs")
        self.conn.sql("INSTALL iceberg")
        self.conn.sql(f"""
            CREATE SECRET (
                TYPE s3,
                KEY_ID '{credentials["BB_R2_ACCESS_KEY_ID"]}',
                SECRET '{credentials["BB_R2_SECRET_ACCESS_KEY"]}',
                ENDPOINT '{credentials["BB_R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com',
                URL_STYLE 'path'
            )
        """)
        return self.conn

    def reset(self):
        if self.conn is not None:
            self.conn.close()
        self.catalog = None
        self.credentials = None
        self.conn = None


config = Config()
