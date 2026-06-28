from .config import config


def describe_table(name: str) -> dict:
    """Describe a table: its context, columns, and partitions.

    Parameters
    ----------
    name : str
        Table identifier.

    Returns
    -------
    dict
        Metadata with ``name``, ``context``, ``columns`` (each
        ``{name, type, description, nullable}``), and ``partitions`` (a mapping
        of partition column to ``{values, default}``). Filter on partition
        columns for the fastest reads.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> bb.describe_table("ukb_ppp.pqtls")["name"]
    'ukb_ppp.pqtls'
    """
    manifest = config.get_manifest()
    if name not in manifest:
        raise ValueError(
            f"Table '{name}' not found in manifest. "
            f"See list_tables() for available tables."
        )

    entry = manifest[name]
    return {
        "name": name,
        "context": entry["context"],
        "columns": entry["columns"],
        "partitions": entry["partitions"],
    }
