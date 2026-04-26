import duckdb

from .config import config


def load_table(name: str, **filters: str) -> duckdb.DuckDBPyRelation:
    """
    Lazily query a table.

    Parameters
    ----------
    name : str
        Table identifier (e.g. 'ukb_ppp.pqtls').
    **filters : str
        Required partition filters (e.g. ancestry='EUR', protein_id='A0FGR8').

    Returns
    -------
    duckdb.DuckDBPyRelation
        A lazy relation that can be further filtered, selected, or collected.

    Raises
    ------
    ConnectionError
        If the catalog cannot be accessed.
    ValueError
        If the table is not found, required filters are missing,
        unknown filters are passed, or filter values are invalid.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>>
    >>> rel = bb.load_table('dbsnp.vcf', assembly='GRCh38', chromosome='22')
    >>> rel = rel.select('rsid, position, ref_allele, alt_allele')
    >>> df = rel.limit(5).fetchdf()

    """
    catalog = config.get_catalog()

    if name not in catalog:
        raise ValueError(
            f"Table '{name}' not found in catalog. "
            f"See list_tables() for available tables."
        )

    entry = catalog[name]
    required = entry["required_filters"]
    allowed_values = entry["allowed_values"]

    missing = [f for f in required if f not in filters]
    if missing:
        raise ValueError(
            f"Missing required filters for '{name}': {', '.join(missing)}. "
            f"Required: {', '.join(required)}."
        )

    unknown = [f for f in filters if f not in required]
    if unknown:
        raise ValueError(
            f"Unknown filters for '{name}': {', '.join(unknown)}. "
            f"Valid filters: {', '.join(required)}."
        )

    coerced = {}
    for col, val in filters.items():
        val = str(val).strip()
        if col in allowed_values:
            allowed = allowed_values[col]
            if val not in allowed:
                lookup = {v.lower(): v for v in allowed}
                val = lookup.get(val.lower())
                if not val:
                    raise ValueError(
                        f"Invalid value '{str(filters[col]).strip()}' for filter '{col}'. "
                        f"Allowed: {', '.join(allowed)}."
                    )
        coerced[col] = val

    query = f"SELECT * FROM iceberg_scan('{entry['metadata_json']}')"

    if coerced:
        conditions = []
        for col, val in coerced.items():
            safe_val = val.replace("'", "''")
            conditions.append(f"{col} = '{safe_val}'")
        query += " WHERE " + " AND ".join(conditions)

    conn = config.get_connection()
    return conn.sql(query)
