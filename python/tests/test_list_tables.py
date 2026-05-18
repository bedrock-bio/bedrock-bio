from bedrock_bio.list_tables import list_tables


class TestListTables:
    def test_returns_list_of_strings(self):
        result = list_tables()
        assert isinstance(result, list)
        for name in result:
            assert isinstance(name, str)
        assert "dbsnp.vcf" in result
