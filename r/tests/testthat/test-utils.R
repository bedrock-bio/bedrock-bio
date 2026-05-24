# --- get_catalog ---

test_that("get_catalog returns a named list of entry lists", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
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
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  first <- bedrockbio:::get_catalog()
  second <- bedrockbio:::get_catalog()
  expect_identical(first, second)
})

test_that("get_catalog errors when URL is unreachable", {
  bedrockbio:::reset()
  pkg <- bedrockbio:::pkg
  original_url <- pkg$catalog_url
  pkg$catalog_url <- "https://invalid.invalid/manifest.json"
  on.exit({
    pkg$catalog_url <- original_url
    bedrockbio:::reset()
  })
  expect_error(
    suppressWarnings(bedrockbio:::get_catalog()),
    "Unable to access manifest URL"
  )
})

test_that("get_catalog preserves whitelisted column keys and strips others", {
  bedrockbio:::reset()
  fixture <- tempfile(fileext = ".json")
  jsonlite::write_json(
    list(
      namespaces = list(
        test_ns = list(
          citation = list(),
          source_url = "https://example.com",
          license = "MIT",
          tables = list(
            test_tbl = list(
              metadata_json = "s3://test/metadata.json",
              description = "test",
              partition_by = list(),
              sort_by = list(),
              columns = list(
                list(
                  name = "col_with_extras",
                  type = "string",
                  description = "desc",
                  nullable = TRUE,
                  allowed_values = list("A", "B"),
                  extra_field = "should_be_stripped",
                  another_extra = 123
                ),
                list(
                  name = "col_minimal",
                  type = "int",
                  description = "minimal"
                )
              )
            )
          )
        )
      )
    ),
    fixture,
    auto_unbox = TRUE
  )

  pkg <- bedrockbio:::pkg
  original_url <- pkg$catalog_url
  pkg$catalog_url <- paste0("file://", fixture)
  on.exit({
    pkg$catalog_url <- original_url
    unlink(fixture)
    bedrockbio:::reset()
  })

  result <- bedrockbio:::get_catalog()
  cols <- result[["test_ns.test_tbl"]]$columns

  c1 <- cols[[1]]
  expect_equal(c1$name, "col_with_extras")
  expect_equal(c1$type, "string")
  expect_equal(c1$description, "desc")
  expect_true(c1$nullable)
  expect_equal(c1$allowed_values, c("A", "B"))
  expect_false("extra_field" %in% names(c1))
  expect_false("another_extra" %in% names(c1))

  c2 <- cols[[2]]
  expect_equal(c2$name, "col_minimal")
  expect_false("nullable" %in% names(c2))
  expect_false("allowed_values" %in% names(c2))
})

# --- get_namespaces ---

test_that("get_namespaces returns a named list of namespace entries", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  result <- bedrockbio:::get_namespaces()
  expect_type(result, "list")
  expect_true(length(result) > 0)
  for (ns_id in names(result)) {
    entry <- result[[ns_id]]
    expect_equal(entry$id, ns_id)
    expect_type(entry$name, "character")
    expect_type(entry$description, "character")
    expect_type(entry$tables, "character")
    expect_true(all(startsWith(entry$tables, paste0(ns_id, "."))))
  }
})

# --- get_credentials ---

test_that("get_credentials returns expected keys", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  result <- bedrockbio:::get_credentials()
  expected_names <- c(
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY"
  )
  expect_true(all(expected_names %in% names(result)))
  for (nm in expected_names) {
    expect_type(result[[nm]], "character")
    expect_true(nzchar(result[[nm]]))
  }
})

test_that("get_credentials caches result", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  first <- bedrockbio:::get_credentials()
  second <- bedrockbio:::get_credentials()
  expect_identical(first, second)
})

test_that("get_credentials errors when URL is unreachable", {
  bedrockbio:::reset()
  pkg <- bedrockbio:::pkg
  original_url <- pkg$credentials_url
  pkg$credentials_url <- "https://invalid.invalid/credentials.json"
  on.exit({
    pkg$credentials_url <- original_url
    bedrockbio:::reset()
  })
  expect_error(
    suppressWarnings(bedrockbio:::get_credentials()),
    "Unable to fetch credentials"
  )
})

# --- get_connection ---

test_that("get_connection returns DuckDB with S3 secret", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  conn <- bedrockbio:::get_connection()
  expect_s4_class(conn, "duckdb_connection")
  secrets <- DBI::dbGetQuery(conn, "FROM duckdb_secrets()")
  expect_equal(nrow(secrets), 1L)
  expect_equal(secrets$type, "s3")
  expect_true(grepl("r2.cloudflarestorage.com", secrets$secret_string))
})

test_that("get_connection caches", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::reset()
  first <- bedrockbio:::get_connection()
  second <- bedrockbio:::get_connection()
  expect_identical(first, second)
})

test_that("reset clears cached catalog, namespaces, credentials, and conn", {
  skip_on_cran()
  skip_if_offline()
  bedrockbio:::get_catalog()
  bedrockbio:::get_namespaces()
  bedrockbio:::get_credentials()
  bedrockbio:::get_connection()
  pkg <- bedrockbio:::pkg
  expect_false(is.null(pkg$catalog))
  expect_false(is.null(pkg$namespaces))
  expect_false(is.null(pkg$credentials))
  expect_false(is.null(pkg$conn))
  bedrockbio:::reset()
  expect_null(pkg$catalog)
  expect_null(pkg$namespaces)
  expect_null(pkg$credentials)
  expect_null(pkg$conn)
})
