skip_on_cran()
skip_if_offline()

test_that("errors on unknown namespace", {
  expect_error(
    describe_namespace("not_a_namespace"),
    "not found"
  )
})

test_that("returns expected fields", {
  result <- describe_namespace("ukb_ppp")
  expect_equal(result$id, "ukb_ppp")
  expect_type(result$name, "character")
  expect_true(nzchar(result$name))
  expect_type(result$description, "character")
  expect_type(result$source_url, "character")
  expect_type(result$license, "character")
  expect_type(result$instructions, "character")
  expect_type(result$citation, "list")
})

test_that("tables field is character vector of fully-qualified names", {
  result <- describe_namespace("ukb_ppp")
  expect_type(result$tables, "character")
  expect_true(length(result$tables) > 0)
  expect_true(all(startsWith(result$tables, "ukb_ppp.")))
  expect_true("ukb_ppp.pqtls" %in% result$tables)
})

test_that("tables list agrees with list_tables filtered to namespace", {
  result <- describe_namespace("ukb_ppp")
  from_list <- list_tables()[startsWith(list_tables(), "ukb_ppp.")]
  expect_setequal(result$tables, from_list)
})
