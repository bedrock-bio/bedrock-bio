from .config import config


def reset() -> None:
    """
    Clear cached state (manifest, namespaces, credentials, and the database
    connection).

    The next call to a query function re-fetches the manifest and credentials
    and rebuilds the connection. Useful when credentials have been rotated
    during a long-running session.
    """
    config.reset()
