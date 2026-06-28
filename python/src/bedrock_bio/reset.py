from .config import config


def reset() -> None:
    """Clear cached state (manifest, namespaces, and connection).

    The next call to a query function re-fetches the manifest and rebuilds the
    connection. Useful when the manifest or ``BB_ENV`` has changed during a
    long-running session.
    """
    config.reset()
