import bedrock_bio as bb
from bedrock_bio.config import config


def test_reset_is_exported():
    assert callable(bb.reset)
    assert "reset" in bb.__all__


def test_reset_clears_state():
    config.manifest = {"ns.tbl": {}}
    config.credentials = {"R2_ACCESS_KEY_ID": "x"}
    bb.reset()
    assert config.manifest is None
    assert config.credentials is None
