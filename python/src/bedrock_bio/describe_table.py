from .config import config


def describe_table(name: str) -> dict:
    """
    Describe a table's metadata, citation, and columns.

    Parameters
    ----------
    name : str
        Table identifier (e.g. 'ukb_ppp.pqtls').

    Returns
    -------
    dict
        Table metadata including description, citation, source_url,
        license, partition_by, sort_by, and column definitions.

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
        "description": entry["description"],
        "citation": entry["citation"],
        "source_url": entry["source_url"],
        "license": entry["license"],
        "partition_by": entry["partition_by"],
        "sort_by": entry["sort_by"],
        "columns": entry["columns"],
    }
