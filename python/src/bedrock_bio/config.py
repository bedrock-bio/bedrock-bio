import duckdb
import json
import os
import urllib.request
from dataclasses import dataclass

MANIFEST_VERSION = 2


@dataclass
class Config:
    manifest: dict[str, dict] | None = None
    namespaces: dict[str, dict] | None = None
    conn: duckdb.DuckDBPyConnection | None = None

    @property
    def base_url(self) -> str:
        if os.environ.get("BB_ENV") == "dev":
            return "https://datasets-dev.bedrock.bio"
        return "https://datasets.bedrock.bio"

    @property
    def manifest_url(self) -> str:
        return f"{self.base_url}/manifest.json"

    def _load_manifest(self) -> None:
        if self.manifest is not None:
            return

        try:
            request = urllib.request.Request(
                self.manifest_url, headers={"User-Agent": "bedrock-bio"}
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = json.loads(response.read())

        except Exception:
            raise ConnectionError(
                f"Unable to access manifest URL {self.manifest_url!r}"
            )

        version = raw.get("version")
        if version != MANIFEST_VERSION:
            raise ValueError(
                f"Unsupported manifest version {version!r} at "
                f"{self.manifest_url!r}; this client requires version "
                f"{MANIFEST_VERSION}. Upgrade bedrock-bio to the latest release."
            )

        self.manifest = {}
        self.namespaces = {}

        for ns, ns_data in raw["namespaces"].items():
            table_fqns = []
            for table_name, table in ns_data["tables"].items():
                fqn = f"{ns}.{table_name}"
                table_fqns.append(fqn)

                self.manifest[fqn] = {
                    "iceberg_json": table["iceberg_json"],
                    "partitions": table.get("partitions", {}),
                    "columns": table.get("columns", []),
                    "context": table.get("context", ""),
                }

            self.namespaces[ns] = {
                "name": ns_data.get("name", ""),
                "license": ns_data.get("license", ""),
                "citation": ns_data.get("citation", ""),
                "context": ns_data.get("context", ""),
                "tables": table_fqns,
            }

    def get_manifest(self) -> dict[str, dict]:
        self._load_manifest()
        return self.manifest

    def get_namespaces(self) -> dict[str, dict]:
        self._load_manifest()
        return self.namespaces

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        if self.conn is not None:
            return self.conn

        self.conn = duckdb.connect()
        self.conn.sql("INSTALL httpfs")
        self.conn.sql("INSTALL iceberg")
        self.conn.sql("SET s3_endpoint='bedrock.bio'")
        self.conn.sql("SET s3_url_style='vhost'")
        self.conn.sql("SET s3_use_ssl=true")
        self.conn.sql("SET s3_region='auto'")
        return self.conn


config = Config()
