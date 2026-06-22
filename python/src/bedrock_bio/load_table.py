import duckdb

from .config import config


def load_table(name: str) -> duckdb.DuckDBPyRelation:
    """
    Lazily query a table.

    Parameters
    ----------
    name : str
        Table identifier (e.g. 'ukb_ppp.pqtls').

    Returns
    -------
    duckdb.DuckDBPyRelation
        A lazy relation that can be further filtered, selected, or collected.
        Use ``describe_table(name)`` to see partition columns and per-column
        allowed values; filter on partition columns for fastest reads.

    Raises
    ------
    ConnectionError
        If the manifest cannot be accessed.
    ValueError
        If the table is not found in the manifest.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>>
    >>> rel = bb.load_table('dbsnp.vcf')
    >>> df = (
    ...     rel.filter("assembly = 'GRCh38' AND chromosome = '22'")
    ...        .select('rsid, position, ref_allele, alt_allele')
    ...        .limit(5)
    ...        .df()
    ... )

    """
    manifest = config.get_manifest()

    if name not in manifest:
        raise ValueError(
            f"Table '{name}' not found in manifest. "
            f"See list_tables() for available tables."
        )

    entry = manifest[name]
    conn = config.get_connection()
    escaped = entry["metadata_json"].replace("'", "''")
    return conn.sql(f"SELECT * FROM iceberg_scan('{escaped}')")
