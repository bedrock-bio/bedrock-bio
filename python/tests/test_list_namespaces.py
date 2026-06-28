from bedrock_bio.list_namespaces import list_namespaces
from conftest import requires_live_v2_manifest


class TestListNamespaces:
    def test_returns_list_of_strings(self):
        requires_live_v2_manifest()
        result = list_namespaces()
        assert isinstance(result, list)
        for name in result:
            assert isinstance(name, str)
        assert "dbsnp" in result
