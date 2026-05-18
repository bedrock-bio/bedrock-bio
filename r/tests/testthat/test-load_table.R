skip_on_cran()
skip_if_offline()

dbsnp <- function() {
  load_table("dbsnp.vcf") |>
    dplyr::filter(assembly == "GRCh38", chromosome == "22")
}

test_that("errors on unknown table", {
  expect_error(
    load_table("not_a_table"),
    "not found in catalog"
  )
})

test_that("returns a lazy tbl", {
  expect_s3_class(load_table("dbsnp.vcf"), "tbl_lazy")
})

test_that("filter narrows results", {
  df <- head(dbsnp(), 5) |> dplyr::collect()
  expect_equal(nrow(df), 5L)
  expect_equal(unique(df$chromosome), "22")
})

test_that("select limits columns", {
  df <- dbsnp() |>
    dplyr::select(chromosome, position) |>
    head(5) |>
    dplyr::collect()
  expect_equal(names(df), c("chromosome", "position"))
})
