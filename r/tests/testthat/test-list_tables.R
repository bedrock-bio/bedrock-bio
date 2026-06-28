two_ns_manifest <- list(
  version = 2L,
  namespaces = list(
    ns_a = list(tables = list(
      tbl_one = list(iceberg_json = "s3://test/a1.json"),
      tbl_two = list(iceberg_json = "s3://test/a2.json")
    )),
    ns_b = list(tables = list(
      tbl_three = list(iceberg_json = "s3://test/b1.json")
    ))
  )
)

test_that("list_tables returns a character vector", {
  skip_on_cran()
  skip_if_offline()
  skip_unless_live_v2()
  result <- list_tables()
  expect_type(result, "character")
  expect_true("dbsnp.vcf" %in% result)
})

test_that("no namespace returns all tables", {
  local_manifest(two_ns_manifest)
  expect_setequal(
    list_tables(),
    c("ns_a.tbl_one", "ns_a.tbl_two", "ns_b.tbl_three")
  )
})

test_that("namespace filters to that namespace", {
  local_manifest(two_ns_manifest)
  expect_equal(list_tables("ns_a"), c("ns_a.tbl_one", "ns_a.tbl_two"))
})

test_that("unknown namespace errors", {
  local_manifest(two_ns_manifest)
  expect_error(list_tables("not_a_namespace"), "not found")
})
