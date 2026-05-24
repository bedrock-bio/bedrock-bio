from bedrock_bio.list_namespaces import list_namespaces


class TestListNamespaces:
    def test_returns_list_of_strings(self):
        result = list_namespaces()
        assert isinstance(result, list)
        for name in result:
            assert isinstance(name, str)
        assert "ukb_ppp" in result
        assert "dbsnp" in result
