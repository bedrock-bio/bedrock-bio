from .config import config


def reset() -> None:
    """
    Clear cached state (manifest, namespaces, and the database connection).

    The next call to a query function re-fetches the manifest and rebuilds the
    connection. Useful when the manifest has changed, or ``BB_ENV`` has been
    changed, during a long-running session.
    """
    config.reset()
