from .config import config


def list_tables() -> list[str]:
    """
    List available tables in the Bedrock Bio library.

    Returns
    -------
    list[str]
        A list of table identifiers (e.g. 'ukb_ppp.pqtls').

    Raises
    ------
    ConnectionError
        If the catalog cannot be accessed.

    Examples
    --------
    >>> import bedrock_bio as bb
    >>> bb.list_tables()
    ['ukb_ppp.pqtls', ...]

    """
    catalog = config.get_catalog()
    return list(catalog.keys())
