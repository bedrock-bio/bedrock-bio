from .config import config


def list_tables(namespace: str | None = None) -> list[str]:
    """
    List available tables in the Bedrock Bio library.

    Parameters
    ----------
    namespace : str, optional
        If given, return only the tables in that namespace (e.g. 'ukb_ppp').
        If omitted, return all tables across every namespace.

    Returns
    -------
    list[str]
        A list of fully-qualified table identifiers (e.g. 'ukb_ppp.pqtls').

    Raises
    ------
    ConnectionError
        If the manifest cannot be accessed.
    ValueError
        If ``namespace`` is given but not found.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> bb.list_tables()
    ['ukb_ppp.pqtls', ...]
    >>> bb.list_tables('ukb_ppp')
    ['ukb_ppp.assays', 'ukb_ppp.genes', 'ukb_ppp.pqtls', ...]

    """
    if namespace is None:
        manifest = config.get_manifest()
        return list(manifest.keys())

    namespaces = config.get_namespaces()
    if namespace not in namespaces:
        raise ValueError(
            f"Namespace '{namespace}' not found. "
            f"See list_namespaces() for available namespaces."
        )

    return list(namespaces[namespace]["tables"])
