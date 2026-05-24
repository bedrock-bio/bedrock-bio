skip_on_cran()
skip_if_offline()

test_that("list_namespaces returns a character vector", {
  result <- list_namespaces()
  expect_type(result, "character")
  expect_true("ukb_ppp" %in% result)
  expect_true("dbsnp" %in% result)
})
