from .config import config


def list_namespaces() -> list[str]:
    """
    List available namespaces (data sources) in the Bedrock Bio library.

    Returns
    -------
    list[str]
        A list of namespace identifiers (e.g. 'ukb_ppp').

    Raises
    ------
    ConnectionError
        If the catalog cannot be accessed.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> bb.list_namespaces()
    ['ukb_ppp', ...]

    """
    namespaces = config.get_namespaces()
    return list(namespaces.keys())
