skip_on_cran()

reset_pkg <- function() {
  pkg <- bedrockbio:::pkg
  pkg$catalog <- NULL
  pkg$credentials <- NULL
  if (!is.null(pkg$conn)) {
    try(DBI::dbDisconnect(pkg$conn, shutdown = TRUE), silent = TRUE)
  }
  pkg$conn <- NULL
}

# --- get_catalog ---

test_that("get_catalog returns a named list of entry lists", {
  reset_pkg()
  result <- bedrockbio:::get_catalog()
  expect_type(result, "list")
  expect_true(length(result) > 0)
  for (entry in result) {
    expect_type(entry, "list")
    expect_type(entry$metadata_json, "character")
    expect_type(entry$partition_by, "character")
    expect_type(entry$sort_by, "character")
    expect_type(entry$columns, "list")
  }
})

test_that("get_catalog caches result", {
  reset_pkg()
  first <- bedrockbio:::get_catalog()
  second <- bedrockbio:::get_catalog()
  expect_identical(first, second)
})

# --- get_credentials ---

test_that("get_credentials returns expected keys", {
  reset_pkg()
  result <- bedrockbio:::get_credentials()
  expected_names <- c(
    "BB_R2_ACCOUNT_ID",
    "BB_R2_ACCESS_KEY_ID",
    "BB_R2_SECRET_ACCESS_KEY"
  )
  expect_true(all(expected_names %in% names(result)))
  for (nm in expected_names) {
    expect_type(result[[nm]], "character")
    expect_true(nzchar(result[[nm]]))
  }
})

test_that("get_credentials caches result", {
  reset_pkg()
  first <- bedrockbio:::get_credentials()
  second <- bedrockbio:::get_credentials()
  expect_identical(first, second)
})

# --- get_connection ---

test_that("get_connection returns DuckDB with S3 secret", {
  reset_pkg()
  conn <- bedrockbio:::get_connection()
  expect_s4_class(conn, "duckdb_connection")
  secrets <- DBI::dbGetQuery(conn, "FROM duckdb_secrets()")
  expect_equal(nrow(secrets), 1L)
  expect_equal(secrets$type, "s3")
  expect_true(grepl("r2.cloudflarestorage.com", secrets$secret_string))
})

test_that("get_connection caches", {
  reset_pkg()
  first <- bedrockbio:::get_connection()
  second <- bedrockbio:::get_connection()
  expect_identical(first, second)
})
