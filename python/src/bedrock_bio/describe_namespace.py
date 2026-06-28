from .config import config


def describe_namespace(name: str) -> dict:
    """Describe a namespace: its name, citation, license, context, and tables.

    Parameters
    ----------
    name : str
        Namespace identifier.

    Returns
    -------
    dict
        Metadata with ``name``, ``citation``, ``license``, ``context``, and
        ``tables`` (fully-qualified table identifiers). Use ``describe_table()``
        for per-table details.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> bb.describe_namespace("ukb_ppp")["tables"]
    ['ukb_ppp.assays', 'ukb_ppp.genes', 'ukb_ppp.pqtls', ...]
    """
    namespaces = config.get_namespaces()
    if name not in namespaces:
        raise ValueError(
            f"Namespace '{name}' not found. "
            f"See list_namespaces() for available namespaces."
        )
    return namespaces[name]
