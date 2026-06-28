test_that("errors on unknown namespace", {
  local_v2_manifest()
  expect_error(
    describe_namespace("not_a_namespace"),
    "not found"
  )
})

test_that("returns expected fields", {
  local_v2_manifest()
  result <- describe_namespace("test_ns")
  expect_equal(result$name, "Test Namespace")
  expect_type(result$name, "character")
  expect_true(nzchar(result$name))
  expect_type(result$license, "character")
  # citation is a pre-formatted string in v2.
  expect_type(result$citation, "character")
  expect_type(result$context, "character")
})

test_that("tables field is character vector of fully-qualified names", {
  local_v2_manifest()
  result <- describe_namespace("test_ns")
  expect_type(result$tables, "character")
  expect_true(length(result$tables) > 0)
  expect_true(all(startsWith(result$tables, "test_ns.")))
  expect_true("test_ns.test_tbl" %in% result$tables)
})

test_that("tables list agrees with list_tables filtered to namespace", {
  local_v2_manifest()
  result <- describe_namespace("test_ns")
  from_list <- list_tables()[startsWith(list_tables(), "test_ns.")]
  expect_setequal(result$tables, from_list)
})
