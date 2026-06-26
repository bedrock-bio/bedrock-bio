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

    def test_filters_and_projection_push_down_to_scan(self):
        # Partition filters (assembly, chromosome), a non-partition predicate
        # (position), and a projection must all be pushed into the Iceberg scan
        # rather than applied as separate operators after a full read. This is
        # the partition-pruning / predicate-pushdown that makes the large tables
        # usable; a regression here (e.g. binding the scan path as a parameter)
        # silently disables it.
        plan = (
            load_table("dbsnp.vcf")
            .filter("assembly = 'GRCh38' AND chromosome = '22' AND position > 50000000")
            .select("rsid, position")
            .explain()
        )
        assert "ICEBERG_SCAN" in plan
        # No standalone FILTER operator: all predicates reached the scan.
        assert "FILTER" not in plan
        assert "assembly='GRCh38'" in plan
        assert "chromosome='22'" in plan
        assert "position>50000000" in plan
        # Projection pushed down: unselected columns are pruned from the scan.
        assert "ref_allele" not in plan
        assert "alt_allele" not in plan
