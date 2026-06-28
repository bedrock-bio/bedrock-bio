from .config import config


def list_tables(namespace: str | None = None) -> list[str]:
    """List available tables, optionally filtered to one namespace.

    Parameters
    ----------
    namespace : str, optional
        If given, return only that namespace's tables; otherwise all tables.

    Returns
    -------
    list[str]
        Fully-qualified table identifiers.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> bb.list_tables("ukb_ppp")
    ['ukb_ppp.assays', 'ukb_ppp.genes', 'ukb_ppp.pqtls', ...]
    """
    if namespace is None:
        return list(config.get_manifest().keys())

    namespaces = config.get_namespaces()
    if namespace not in namespaces:
        raise ValueError(
            f"Namespace '{namespace}' not found. "
            f"See list_namespaces() for available namespaces."
        )
    return list(namespaces[namespace]["tables"])
