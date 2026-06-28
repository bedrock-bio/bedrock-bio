from .config import config


def list_namespaces() -> list[str]:
    """List available namespaces (data sources).

    Returns
    -------
    list[str]
        Namespace identifiers.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> bb.list_namespaces()
    ['ukb_ppp', ...]
    """
    return list(config.get_namespaces().keys())
