import duckdb
import pytest

from bedrock_bio.load_table import load_table


class TestLoadTable:
    def test_no_table(self):
        with pytest.raises(ValueError, match="not found in manifest"):
            load_table("not_a_table")

    def test_returns_relation(self):
        rel = load_table("dbsnp.vcf")
        assert isinstance(rel, duckdb.DuckDBPyRelation)

    def test_select(self):
        rel = (
            load_table("dbsnp.vcf")
            .filter("assembly = 'GRCh38' AND chromosome = '22'")
            .select("chromosome", "position")
            .limit(5)
        )
        assert rel.columns == ["chromosome", "position"]

    def test_filter_narrows(self):
        rel = (
            load_table("dbsnp.vcf")
            .filter("assembly = 'GRCh38' AND chromosome = '22'")
            .limit(5)
        )
        rows = rel.fetchall()
        assert len(rows) == 5
        chromosome_idx = rel.columns.index("chromosome")
        assert {row[chromosome_idx] for row in rows} == {"22"}
