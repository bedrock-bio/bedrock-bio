skip_on_cran()
skip_if_offline()

test_that("list_tables returns a character vector", {
  skip_unless_live_v2()
  result <- list_tables()
  expect_type(result, "character")
  expect_true("dbsnp.vcf" %in% result)
})
