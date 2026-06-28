from bedrock_bio.config import config


def test_default_uses_prod_host(monkeypatch):
    monkeypatch.delenv("BB_ENV", raising=False)
    assert config.base_url == "https://datasets.bedrock.bio"
    assert config.manifest_url == "https://datasets.bedrock.bio/manifest.json"


def test_dev_uses_dev_host(monkeypatch):
    monkeypatch.setenv("BB_ENV", "dev")
    assert config.base_url == "https://datasets-dev.bedrock.bio"
    assert config.manifest_url == "https://datasets-dev.bedrock.bio/manifest.json"
