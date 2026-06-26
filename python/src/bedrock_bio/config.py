import duckdb
import json
import os
import urllib.request
from dataclasses import dataclass

# Column keys preserved from the manifest, in this order.
COLUMN_FIELDS = ("name", "type", "description", "nullable", "allowed_values")


@dataclass
class Config:
    manifest: dict[str, dict] | None = None
    namespaces: dict[str, dict] | None = None
    conn: duckdb.DuckDBPyConnection | None = None

    @property
    def base_url(self) -> str:
        if os.environ.get("BB_ENV") == "dev":
            return "https://data-dev.bedrock.bio"
        else:
            return "https://data.bedrock.bio"

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
            # Bound network stalls on the manifest fetch (seconds).
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = json.loads(response.read())

        except Exception:
            raise ConnectionError(
                f"Unable to access manifest URL {self.manifest_url!r}"
            )

        self.manifest = {}
        self.namespaces = {}

        for ns, ns_data in raw["namespaces"].items():
            table_fqns = []
            for table_name, metadata in ns_data["tables"].items():
                fqn = f"{ns}.{table_name}"
                table_fqns.append(fqn)

                self.manifest[fqn] = {
                    "metadata_json": metadata["metadata_json"],
                    "partition_by": list(metadata.get("partition_by", [])),
                    "sort_by": list(metadata.get("sort_by", [])),
                    "description": metadata.get("description", ""),
                    "citation": ns_data.get("citation"),
                    "source_url": ns_data.get("source_url", ""),
                    "license": ns_data.get("license", ""),
                    "columns": [
                        {tf: col[tf] for tf in COLUMN_FIELDS if tf in col}
                        for col in metadata.get("columns", [])
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
        # Anonymous, cache-fronted reads over the public custom domain. Each
        # table's metadata_json is s3://<bucket>/...; vhost resolution maps it to
        # https://<bucket>.bedrock.bio/... — no credentials, no S3 API, no listing.
        # The connection is private to this package, so global SET is safe here.
        self.conn.sql("SET s3_endpoint='bedrock.bio'")
        self.conn.sql("SET s3_url_style='vhost'")
        self.conn.sql("SET s3_use_ssl=true")
        self.conn.sql("SET s3_region='auto'")
        return self.conn

    def reset(self):
        if self.conn is not None:
            self.conn.close()
        self.manifest = None
        self.namespaces = None
        self.conn = None


config = Config()
