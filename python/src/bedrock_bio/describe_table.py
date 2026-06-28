from .config import config


def describe_table(name: str) -> dict:
    """
    Describe a table: its context, columns, and partitions.

    Parameters
    ----------
    name : str
        Table identifier (e.g. 'ukb_ppp.pqtls').

    Returns
    -------
    dict
        Table metadata: ``name``, ``context`` (prose: what the table is, how to
        query it, sort/related-table hints), ``columns`` (a list of
        ``{name, type, description, nullable}``), and ``partitions`` (a mapping
        of partition column to ``{values, default}``). Filter on partition
        columns for the fastest reads.

    Raises
    ------
    ConnectionError
        If the manifest cannot be accessed.
    ValueError
        If the table is not found in the manifest.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> info = bb.describe_table('ukb_ppp.pqtls')
    >>> info['name']
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
