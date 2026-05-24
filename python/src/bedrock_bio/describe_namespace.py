from .config import config


def describe_namespace(name: str) -> dict:
    """
    Describe a namespace's metadata, citation, license, and tables.

    Parameters
    ----------
    name : str
        Namespace identifier (e.g. 'ukb_ppp').

    Returns
    -------
    dict
        Namespace metadata with id, name, description, source_url, license,
        instructions, citation, and tables (list of fully-qualified table
        identifiers). Use ``describe_table()`` for per-table details.

    Raises
    ------
    ConnectionError
        If the catalog cannot be accessed.
    ValueError
        If the namespace is not found.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> info = bb.describe_namespace('ukb_ppp')
    >>> info['tables']
    ['ukb_ppp.assays', 'ukb_ppp.genes', 'ukb_ppp.pqtls', ...]

    """
    namespaces = config.get_namespaces()

    if name not in namespaces:
        raise ValueError(
            f"Namespace '{name}' not found. "
            f"See list_namespaces() for available namespaces."
        )

    return namespaces[name]
