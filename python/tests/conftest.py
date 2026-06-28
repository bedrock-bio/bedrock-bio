from bedrock_bio.config import config
import pytest


@pytest.fixture(autouse=True)
def reset():
    config.reset()
    yield
    config.reset()


def requires_live_v2_manifest():
    """Skip a test when the live manifest can't be fetched or isn't v2 yet.

    The v2 prod/dev manifest is published by a separate Dagster job (Gate 0);
    until that runs, the live manifest is still v1 and the version gate raises.
    These live end-to-end tests are expected to skip in that window.
    """
    try:
        config.get_manifest()
    except Exception as exc:  # ConnectionError (offline) or ValueError (v1)
        pytest.skip(f"live v2 manifest unavailable: {exc}")
