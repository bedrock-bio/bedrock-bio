skip_on_cran()
skip_if_offline()

test_that("list_tables returns a character vector", {
  result <- list_tables()
  expect_type(result, "character")
  expect_true("dbsnp.vcf" %in% result)
})
