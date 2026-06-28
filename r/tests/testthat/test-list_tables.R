skip_on_cran()
skip_if_offline()

# A two-namespace v2 fixture so namespace filtering can be checked for exclusion
# (the shared local_v2_manifest() has a single namespace). Points the package's
# manifest_url at a temp file for the duration of the calling test.
local_two_ns_manifest <- function(env = parent.frame()) {
  manifest <- list(
    version = 2L,
    published_at = "2026-06-27T00:00:00Z",
    namespaces = list(
      ns_a = list(
        name = "Namespace A",
        license = "CC0 1.0",
        citation = "Author. Journal 2025. doi:10.0/a",
        context = "What ns_a is.",
        tables = list(
          tbl_one = list(
            partitions = list(),
            iceberg_json = "s3://test/a1.json",
            columns = list(),
            context = ""
          ),
          tbl_two = list(
            partitions = list(),
            iceberg_json = "s3://test/a2.json",
            columns = list(),
            context = ""
          )
        )
      ),
      ns_b = list(
        name = "Namespace B",
        license = "CC0 1.0",
        citation = "Author. Journal 2025. doi:10.0/b",
        context = "What ns_b is.",
        tables = list(
          tbl_three = list(
            partitions = list(),
            iceberg_json = "s3://test/b1.json",
            columns = list(),
            context = ""
          )
        )
      )
    )
  )
  fixture <- tempfile(fileext = ".json")
  jsonlite::write_json(manifest, fixture, auto_unbox = TRUE)
  pkg <- bedrockbio:::pkg
  original_url <- pkg$manifest_url
  pkg$manifest <- NULL
  pkg$namespaces <- NULL
  pkg$manifest_url <- paste0("file://", fixture)
  withr::defer(
    {
      pkg$manifest_url <- original_url
      pkg$manifest <- NULL
      pkg$namespaces <- NULL
      unlink(fixture)
    },
    envir = env
  )
  invisible(fixture)
}

test_that("list_tables returns a character vector", {
  skip_unless_live_v2()
  result <- list_tables()
  expect_type(result, "character")
  expect_true("dbsnp.vcf" %in% result)
})

test_that("no namespace returns all tables", {
  local_two_ns_manifest()
  expect_setequal(
    list_tables(),
    c("ns_a.tbl_one", "ns_a.tbl_two", "ns_b.tbl_three")
  )
})

test_that("namespace filters to that namespace", {
  local_two_ns_manifest()
  expect_equal(list_tables("ns_a"), c("ns_a.tbl_one", "ns_a.tbl_two"))
})

test_that("unknown namespace errors", {
  local_two_ns_manifest()
  expect_error(list_tables("not_a_namespace"), "not found")
})
