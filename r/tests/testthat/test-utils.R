# --- get_manifest ---

test_that("get_manifest returns a named list of v2 entry lists", {
  local_v2_manifest()
  result <- bedrockbio:::get_manifest()
  expect_type(result, "list")
  expect_true(length(result) > 0)
  for (entry in result) {
    expect_type(entry, "list")
    expect_type(entry$iceberg_json, "character")
    expect_type(entry$partitions, "list")
    expect_type(entry$columns, "list")
    expect_type(entry$context, "character")
  }
})

test_that("get_manifest caches result", {
  local_v2_manifest()
  first <- bedrockbio:::get_manifest()
  second <- bedrockbio:::get_manifest()
  expect_identical(first, second)
})

test_that("get_manifest errors when URL is unreachable", {
  bedrockbio:::reset()
  pkg <- bedrockbio:::pkg
  original_url <- pkg$manifest_url
  pkg$manifest_url <- "https://invalid.invalid/manifest.json"
  on.exit({
    pkg$manifest_url <- original_url
    bedrockbio:::reset()
  })
  expect_error(
    suppressWarnings(bedrockbio:::get_manifest()),
    "Unable to access manifest URL"
  )
})

test_that("get_manifest rejects an unsupported manifest version", {
  bedrockbio:::reset()
  fixture <- tempfile(fileext = ".json")
  jsonlite::write_json(
    list(version = 1L, namespaces = list()),
    fixture,
    auto_unbox = TRUE
  )
  pkg <- bedrockbio:::pkg
  original_url <- pkg$manifest_url
  pkg$manifest_url <- paste0("file://", fixture)
  on.exit({
    pkg$manifest_url <- original_url
    unlink(fixture)
    bedrockbio:::reset()
  })
  expect_error(
    bedrockbio:::get_manifest(),
    "Unsupported manifest version"
  )
})

test_that("get_manifest lifts the v2 table block", {
  local_v2_manifest()
  result <- bedrockbio:::get_manifest()
  entry <- result[["test_ns.test_tbl"]]

  expect_equal(entry$iceberg_json, "s3://test/metadata.json")
  expect_equal(entry$context, "What this table is and how to query it.")
  expect_equal(entry$partitions$release$default, "26.03.0")
  expect_equal(
    unlist(entry$partitions$release$values),
    c("26.03.0", "26.02.0")
  )
  expect_equal(entry$partitions$chromosome$default, "")

  # Columns are lifted wholesale; v2 carries no allowed_values.
  c1 <- entry$columns[[1]]
  expect_equal(c1$name, "disease_id")
  expect_equal(c1$type, "TEXT")
  expect_equal(c1$description, "An identifier.")
  expect_false(c1$nullable)
  for (col in entry$columns) {
    expect_false("allowed_values" %in% names(col))
  }
})

# --- get_namespaces ---

test_that("get_namespaces lifts the v2 namespace block", {
  local_v2_manifest()
  result <- bedrockbio:::get_namespaces()
  ns <- result[["test_ns"]]
  expect_equal(ns$name, "Test Namespace")
  expect_equal(ns$license, "CC0 1.0")
  # citation is a pre-formatted string in v2, not a structured object.
  expect_type(ns$citation, "character")
  expect_equal(ns$citation, "Some Author. Some Journal 2025. doi:10.0/test")
  expect_equal(ns$context, "What this data source is and how to use it.")
  expect_equal(ns$tables, "test_ns.test_tbl")
})

test_that("get_namespaces returns a named list of namespace entries", {
  local_v2_manifest()
  result <- bedrockbio:::get_namespaces()
  expect_type(result, "list")
  expect_true(length(result) > 0)
  for (ns_id in names(result)) {
    entry <- result[[ns_id]]
    expect_type(entry$name, "character")
    expect_type(entry$citation, "character")
    expect_type(entry$license, "character")
    expect_type(entry$context, "character")
    expect_type(entry$tables, "character")
    expect_true(all(startsWith(entry$tables, paste0(ns_id, "."))))
  }
})

# --- get_connection ---

test_that("get_connection uses anonymous vhost settings", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  conn <- bedrockbio:::get_connection()
  expect_s4_class(conn, "duckdb_connection")
  secrets <- DBI::dbGetQuery(conn, "FROM duckdb_secrets()")
  expect_equal(nrow(secrets), 0L)
  sql <- "SELECT current_setting('s3_endpoint') AS v"
  expect_equal(DBI::dbGetQuery(conn, sql)$v, "bedrock.bio")
})

test_that("get_connection caches", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  first <- bedrockbio:::get_connection()
  second <- bedrockbio:::get_connection()
  expect_identical(first, second)
})
