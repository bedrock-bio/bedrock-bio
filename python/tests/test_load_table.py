import duckdb
import pytest

from bedrock_bio.load_table import load_table
from conftest import requires_live_v2_manifest


class TestLoadTable:
    def test_errors_on_unknown_table(self):
        requires_live_v2_manifest()
        with pytest.raises(ValueError, match="not found in manifest"):
            load_table("not_a_table")

    def test_returns_relation(self):
        requires_live_v2_manifest()
        assert isinstance(load_table("dbsnp.vcf"), duckdb.DuckDBPyRelation)

    def test_filter_narrows(self):
        requires_live_v2_manifest()
        rel = (
            load_table("dbsnp.vcf")
            .filter("assembly = 'GRCh38' AND chromosome = '22'")
            .limit(5)
        )
        rows = rel.fetchall()
        assert len(rows) == 5
        chromosome = rel.columns.index("chromosome")
        assert {row[chromosome] for row in rows} == {"22"}

    def test_select_limits_columns(self):
        requires_live_v2_manifest()
        rel = (
            load_table("dbsnp.vcf")
            .filter("assembly = 'GRCh38' AND chromosome = '22'")
            .select("chromosome", "position")
            .limit(5)
        )
        assert rel.columns == ["chromosome", "position"]

    def test_filters_and_projection_push_down_to_scan(self):
        requires_live_v2_manifest()
        plan = (
            load_table("dbsnp.vcf")
            .filter("assembly = 'GRCh38' AND chromosome = '22' AND position > 50000000")
            .select("rsid, position")
            .explain()
        )
        assert "ICEBERG_SCAN" in plan
        assert "FILTER" not in plan
        assert "assembly='GRCh38'" in plan
        assert "chromosome='22'" in plan
        assert "position>50000000" in plan
        assert "ref_allele" not in plan
        assert "alt_allele" not in plan

    def test_reads_second_real_table(self):
        requires_live_v2_manifest()
        rows = load_table("ensembl.taxonomies").limit(3).fetchall()
        assert len(rows) == 3
