flat_manifest <- list(
  version = 2L,
  namespaces = list(
    test_ns = list(tables = list(
      flat_tbl = list(
        partitions = list(),
        iceberg_json = "s3://test/metadata.json",
        context = "A single-file table with no partitions."
      )
    ))
  )
)

test_that("errors on unknown table", {
  local_v2_manifest()
  expect_error(describe_table("not_a_table"), "not found in manifest")
})

test_that("returns expected fields", {
  local_v2_manifest()
  result <- describe_table("test_ns.test_tbl")
  expect_equal(result$name, "test_ns.test_tbl")
  expect_true(nzchar(result$context))
  expect_true(length(result$columns) > 0)
  expect_type(result$partitions, "list")
})

test_that("columns have expected fields", {
  local_v2_manifest()
  fields <- c("name", "type", "description", "nullable")
  for (col in describe_table("test_ns.test_tbl")$columns) {
    expect_true(all(fields %in% names(col)))
    expect_false("allowed_values" %in% names(col))
  }
})

test_that("partitioned table returns a partition block", {
  local_v2_manifest()
  partitions <- describe_table("test_ns.test_tbl")$partitions
  expect_true("release" %in% names(partitions))
  expect_true("chromosome" %in% names(partitions))
  for (col in partitions) {
    expect_true(all(c("values", "default") %in% names(col)))
  }
})

test_that("unpartitioned table returns empty partitions", {
  local_manifest(flat_manifest)
  expect_length(describe_table("test_ns.flat_tbl")$partitions, 0)
})
