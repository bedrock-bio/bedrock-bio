from .config import config


def describe_namespace(name: str) -> dict:
    """
    Describe a namespace: its name, citation, license, context, and tables.

    Parameters
    ----------
    name : str
        Namespace identifier (e.g. 'ukb_ppp').

    Returns
    -------
    dict
        Namespace metadata with ``name``, ``citation`` (a ready-to-cite
        string), ``license``, ``context`` (prose: what the data source is,
        where it's from, how to use it), and ``tables`` (list of
        fully-qualified table identifiers). Use ``describe_table()`` for
        per-table details.

    Raises
    ------
    ConnectionError
        If the manifest cannot be accessed.
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
