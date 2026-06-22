import duckdb
import json
import os
import urllib.request
from dataclasses import dataclass


@dataclass
class Config:
    manifest: dict[str, dict] | None = None
    namespaces: dict[str, dict] | None = None
    credentials: dict[str, str] | None = None
    conn: duckdb.DuckDBPyConnection | None = None

    @property
    def base_url(self) -> str:
        if os.environ.get('BB_ENV') == 'dev':
            return 'https://data-dev.bedrock.bio'
        else:
            return 'https://data.bedrock.bio'

    @property
    def manifest_url(self) -> str:
        return f'{self.base_url}/manifest.json'

    @property
    def credentials_url(self) -> str:
        return f'{self.base_url}/credentials.json'

    @property
    def timeout(self) -> int:
        return 10

    @property
    def table_fields(self) -> tuple[str]:
        return ('name', 'type', 'description', 'nullable', 'allowed_values')

    def _load_manifest(self) -> None:
        if self.manifest is not None:
            return

        try:
            request = urllib.request.Request(
                self.manifest_url, headers={'User-Agent': 'bedrock-bio'}
            )
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                raw = json.loads(response.read())

        except Exception:
            raise ConnectionError(f'Unable to access manifest URL {self.manifest_url!r}')

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
                        {tf: col[tf] for tf in self.table_fields if tf in col}
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

    def get_credentials(self) -> dict[str, str]:
        if self.credentials is not None:
            return self.credentials

        try:
            request = urllib.request.Request(
                self.credentials_url, headers={"User-Agent": "bedrock-bio"}
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                self.credentials = json.loads(response.read())

        except Exception:
            raise ConnectionError(f'Unable to access credentials URL {self.credentials_url!r}')

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
        self.manifest = None
        self.namespaces = None
        self.credentials = None
        self.conn = None


config = Config()
