import duckdb

from .config import config


def load_table(name: str) -> duckdb.DuckDBPyRelation:
    """Lazily query a table.

    Parameters
    ----------
    name : str
        Table identifier.

    Returns
    -------
    duckdb.DuckDBPyRelation
        A lazy relation that can be further filtered, selected, or collected.
        Filter on partition columns (see ``describe_table()``) for fastest reads.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> df = (
    ...     bb.load_table("dbsnp.vcf")
    ...     .filter("assembly = 'GRCh38' AND chromosome = '22'")
    ...     .select("rsid, position, ref_allele, alt_allele")
    ...     .limit(5)
    ...     .df()
    ... )
    """
    manifest = config.get_manifest()
    if name not in manifest:
        raise ValueError(
            f"Table '{name}' not found in manifest. "
            f"See list_tables() for available tables."
        )

    conn = config.get_connection()
    escaped = manifest[name]["iceberg_json"].replace("'", "''")
    return conn.sql(f"SELECT * FROM iceberg_scan('{escaped}')")
