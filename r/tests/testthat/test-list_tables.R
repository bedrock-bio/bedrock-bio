skip_on_cran()

test_that("list_tables returns a character vector", {
  result <- list_tables()
  expect_type(result, "character")
})
