skip_on_cran()

test_that("errors on unknown table", {
  expect_error(
    describe_table("not_a_table"),
    "not found in catalog"
  )
})

test_that("returns expected fields", {
  result <- describe_table("ukb_ppp.pqtls")
  expect_equal(result$name, "ukb_ppp.pqtls")
  expect_type(result$description, "character")
  expect_true(nzchar(result$description))
  expect_type(result$citation, "list")
  expect_type(result$source_url, "character")
  expect_type(result$license, "character")
  expect_type(result$columns, "list")
  expect_true(length(result$columns) > 0)
})

test_that("columns have expected fields", {
  result <- describe_table("dbsnp.vcf")
  for (col in result$columns) {
    expect_true("name" %in% names(col))
    expect_true("type" %in% names(col))
    expect_true("description" %in% names(col))
  }
})
