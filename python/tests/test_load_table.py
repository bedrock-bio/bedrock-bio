import duckdb
import pytest

from bedrock_bio.load_table import load_table


class TestLoadTable:
    def test_no_table(self):
        with pytest.raises(ValueError, match="not found in catalog"):
            load_table("not_a_table")

    def test_missing_filters(self):
        with pytest.raises(ValueError, match="Missing required filters"):
            load_table("dbsnp.vcf")

    def test_unknown_filter(self):
        with pytest.raises(ValueError, match="Unknown filters"):
            load_table(
                "dbsnp.vcf",
                assembly="GRCh38",
                chromosome="22",
                fake="value",
            )

    def test_invalid_allowed_value(self):
        with pytest.raises(ValueError, match="Invalid value"):
            load_table("dbsnp.vcf", assembly="INVALID", chromosome="22")

    def test_coerces_int_to_string(self):
        result = load_table("dbsnp.vcf", assembly="GRCh38", chromosome=22)
        assert isinstance(result, duckdb.DuckDBPyRelation)

    def test_coerces_case(self):
        result = load_table("dbsnp.vcf", assembly="grch38", chromosome="22")
        assert isinstance(result, duckdb.DuckDBPyRelation)

    def test_no_filters_for_dummy_partition(self):
        result = load_table("ukb_ppp.assays")
        assert isinstance(result, duckdb.DuckDBPyRelation)

    def test_filters_in_query(self):
        result = load_table("dbsnp.vcf", assembly="GRCh38", chromosome="22")
        plan = result.explain()
        assert "assembly" in plan
        assert "chromosome" in plan

    def test_collect(self):
        result = load_table("dbsnp.vcf", assembly="GRCh38", chromosome="22")
        rows = result.limit(5).fetchall()
        assert len(rows) == 5

    def test_select(self):
        result = (
            load_table("dbsnp.vcf", assembly="GRCh38", chromosome="22")
            .select("chromosome", "position")
            .limit(5)
        )
        assert result.columns == ["chromosome", "position"]

    def test_filter(self):
        result = load_table("dbsnp.vcf", assembly="GRCh38", chromosome="22").limit(5)
        rows = result.fetchall()
        assert len(rows) == 5

        chromosome_idx = result.columns.index("chromosome")
        unique_values = {row[chromosome_idx] for row in rows}
        assert unique_values == {"22"}
