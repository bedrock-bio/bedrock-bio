skip_on_cran()
skip_if_offline()

dbsnp <- function() {
  load_table("dbsnp.vcf") |>
    dplyr::filter(assembly == "GRCh38", chromosome == "22")
}

test_that("errors on unknown table", {
  skip_unless_live_v2()
  expect_error(
    load_table("not_a_table"),
    "not found in manifest"
  )
})

test_that("returns a lazy tbl", {
  skip_unless_live_v2()
  expect_s3_class(load_table("dbsnp.vcf"), "tbl_lazy")
})

test_that("filter narrows results", {
  skip_unless_live_v2()
  df <- head(dbsnp(), 5) |> dplyr::collect()
  expect_equal(nrow(df), 5L)
  expect_equal(unique(df$chromosome), "22")
})

test_that("select limits columns", {
  skip_unless_live_v2()
  df <- dbsnp() |>
    dplyr::select(chromosome, position) |>
    head(5) |>
    dplyr::collect()
  expect_equal(names(df), c("chromosome", "position"))
})

test_that("filters and projection are pushed into the scan", {
  skip_unless_live_v2()
  # Partition filters (assembly, chromosome), a non-partition predicate
  # (position), and a projection must all be pushed into the Iceberg scan
  # rather than applied after a full read -- the partition-pruning /
  # predicate-pushdown that makes the large tables usable.
  rel <- load_table("dbsnp.vcf") |>
    dplyr::filter(
      assembly == "GRCh38",
      chromosome == "22",
      position > 50000000L
    ) |>
    dplyr::select(rsid, position)
  con <- dbplyr::remote_con(rel)
  plan <- DBI::dbGetQuery(con, paste("EXPLAIN", dbplyr::sql_render(rel)))
  plan_text <- paste(unlist(plan), collapse = "\n")

  expect_match(plan_text, "ICEBERG_SCAN")
  # No standalone FILTER operator: all predicates reached the scan.
  expect_false(grepl("FILTER", plan_text))
  expect_match(plan_text, "assembly='GRCh38'")
  expect_match(plan_text, "chromosome='22'")
  expect_match(plan_text, "50000000")
  # Projection pushed down: unselected columns are pruned from the scan.
  expect_false(grepl("ref_allele", plan_text))
  expect_false(grepl("alt_allele", plan_text))
})

test_that("reads an unpartitioned table", {
  skip_unless_live_v2()
  # The other table shape: a single-file table with no partition columns
  # (dbsnp.vcf above is hive-partitioned).
  df <- load_table("ensembl.taxonomies") |>
    head(3) |>
    dplyr::collect()
  expect_equal(nrow(df), 3L)
  expect_true(ncol(df) > 0)
})
