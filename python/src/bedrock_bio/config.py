import duckdb
import json
import urllib.request
from dataclasses import dataclass

CATALOG_URL = "https://data.bedrock.bio/manifest.json"
CREDENTIALS_URL = "https://data.bedrock.bio/credentials.json"
COLUMN_FIELDS = ("name", "type", "description", "nullable", "allowed_values")


@dataclass
class Config:
    catalog: dict[str, dict] | None = None
    namespaces: dict[str, dict] | None = None
    credentials: dict[str, str] | None = None
    conn: duckdb.DuckDBPyConnection | None = None

    def _load_manifest(self) -> None:
        if self.catalog is not None:
            return

        try:
            request = urllib.request.Request(
                CATALOG_URL, headers={"User-Agent": "bedrock-bio"}
            )
            with urllib.request.urlopen(request) as response:
                raw = json.loads(response.read())
        except Exception:
            raise ConnectionError(
                f"Unable to access manifest URL '{CATALOG_URL}'. "
                "Check internet connection and try again."
            )

        self.catalog = {}
        self.namespaces = {}
        for ns, ns_data in raw["namespaces"].items():
            table_fqns = []
            for table_name, meta in ns_data["tables"].items():
                fqn = f"{ns}.{table_name}"
                table_fqns.append(fqn)
                self.catalog[fqn] = {
                    "metadata_json": meta["metadata_json"],
                    "partition_by": list(meta.get("partition_by", [])),
                    "sort_by": list(meta.get("sort_by", [])),
                    "description": meta.get("description", ""),
                    "citation": ns_data.get("citation"),
                    "source_url": ns_data.get("source_url", ""),
                    "license": ns_data.get("license", ""),
                    "columns": [
                        {k: col[k] for k in COLUMN_FIELDS if k in col}
                        for col in meta.get("columns", [])
                    ],
                }

            self.namespaces[ns] = {
                "id": ns,
                "name": ns_data.get("name", ""),
                "description": ns_data.get("description", ""),
                "source_url": ns_data.get("source_url", ""),
                "license": ns_data.get("license", ""),
                "instructions": ns_data.get("instructions", ""),
                "citation": ns_data.get("citation"),
                "tables": table_fqns,
            }

    def get_catalog(self) -> dict[str, dict]:
        self._load_manifest()
        return self.catalog

    def get_namespaces(self) -> dict[str, dict]:
        self._load_manifest()
        return self.namespaces

    def get_credentials(self) -> dict[str, str]:
        if self.credentials is not None:
            return self.credentials

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
        self.conn.execute(
            "CREATE SECRET (TYPE s3, KEY_ID ?, SECRET ?, ENDPOINT ?, URL_STYLE 'path')",
            [
                credentials["R2_ACCESS_KEY_ID"],
                credentials["R2_SECRET_ACCESS_KEY"],
                f"{credentials['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            ],
        )
        return self.conn

    def reset(self):
        if self.conn is not None:
            self.conn.close()
        self.catalog = None
        self.namespaces = None
        self.credentials = None
        self.conn = None


config = Config()
