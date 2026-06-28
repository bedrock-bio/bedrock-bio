from bedrock_bio.list_tables import list_tables
from conftest import requires_live_v2_manifest


class TestListTables:
    def test_returns_list_of_strings(self):
        requires_live_v2_manifest()
        result = list_tables()
        assert isinstance(result, list)
        for name in result:
            assert isinstance(name, str)
        assert "dbsnp.vcf" in result
