test_that("errors on unknown table", {
  local_v2_manifest()
  expect_error(
    describe_table("not_a_table"),
    "not found in manifest"
  )
})

test_that("returns expected fields", {
  local_v2_manifest()
  result <- describe_table("test_ns.test_tbl")
  expect_equal(result$name, "test_ns.test_tbl")
  expect_type(result$context, "character")
  expect_true(nzchar(result$context))
  expect_type(result$columns, "list")
  expect_true(length(result$columns) > 0)
  expect_type(result$partitions, "list")
})

test_that("columns have expected fields and no allowed_values", {
  local_v2_manifest()
  result <- describe_table("test_ns.test_tbl")
  for (col in result$columns) {
    expect_true("name" %in% names(col))
    expect_true("type" %in% names(col))
    expect_true("description" %in% names(col))
    expect_true("nullable" %in% names(col))
    expect_false("allowed_values" %in% names(col))
  }
})

test_that("partitioned table returns a partition block", {
  local_v2_manifest()
  result <- describe_table("test_ns.test_tbl")
  expect_true("release" %in% names(result$partitions))
  expect_true("chromosome" %in% names(result$partitions))
  for (col in result$partitions) {
    expect_true("values" %in% names(col))
    expect_true("default" %in% names(col))
  }
})
