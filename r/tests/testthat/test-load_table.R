skip_on_cran()

dbsnp <- function(...) {
  load_table(
    "dbsnp.vcf",
    assembly = "GRCh38",
    chromosome = "22",
    ...
  )
}

test_that("errors on unknown table", {
  expect_error(
    load_table("not_a_table"),
    "not found in catalog"
  )
})

test_that("errors on missing filters", {
  expect_error(
    load_table("dbsnp.vcf"),
    "Missing required filters"
  )
})

test_that("errors on unknown filter", {
  expect_error(
    dbsnp(fake = "value"),
    "Unknown filters"
  )
})

test_that("errors on invalid allowed value", {
  expect_error(
    load_table(
      "dbsnp.vcf",
      assembly = "INVALID",
      chromosome = "22"
    ),
    "Invalid value"
  )
})

test_that("coerces int to string", {

  result <- load_table(
    "dbsnp.vcf",
    assembly = "GRCh38",
    chromosome = 22
  )
  expect_s3_class(result, "tbl_lazy")
})

test_that("coerces case", {

  result <- load_table(
    "dbsnp.vcf",
    assembly = "grch38",
    chromosome = "22"
  )
  expect_s3_class(result, "tbl_lazy")
})

test_that("no filters needed for dummy partition", {

  result <- load_table("ukb_ppp.assays")
  expect_s3_class(result, "tbl_lazy")
})

test_that("returns a lazy tbl", {

  expect_s3_class(dbsnp(), "tbl_lazy")
})

test_that("collect returns data", {

  df <- head(dbsnp(), 5) |> dplyr::collect()
  expect_equal(nrow(df), 5L)
})

test_that("select limits columns", {

  df <- dbsnp() |>
    dplyr::select(chromosome, position) |>
    head(5) |>
    dplyr::collect()
  expect_equal(names(df), c("chromosome", "position"))
})

test_that("filter narrows results", {

  df <- head(dbsnp(), 5) |> dplyr::collect()
  expect_equal(nrow(df), 5L)
  expect_equal(unique(df$chromosome), "22")
})
