# A hand-built v2 manifest derived from docs/MANIFEST.md, used to unit-test the
# parser without a live network fetch.
v2_manifest <- function() {
  list(
    version = 2L,
    published_at = "2026-06-27T00:00:00Z",
    namespaces = list(
      test_ns = list(
        name = "Test Namespace",
        license = "CC0 1.0",
        citation = "Some Author. Some Journal 2025. doi:10.0/test",
        context = "What this data source is and how to use it.",
        tables = list(
          test_tbl = list(
            partitions = list(
              release = list(
                values = list("26.03.0", "26.02.0"),
                default = "26.03.0"
              ),
              chromosome = list(values = list("1", "22"), default = "")
            ),
            iceberg_json = "s3://test/metadata.json",
            columns = list(
              list(
                name = "disease_id",
                type = "TEXT",
                description = "An identifier.",
                nullable = FALSE
              ),
              list(
                name = "score",
                type = "DOUBLE",
                description = "A score.",
                nullable = TRUE
              )
            ),
            context = "What this table is and how to query it."
          )
        )
      )
    )
  )
}

# Write the v2 fixture to a temp file and point the package's manifest_url at it
# for the duration of the calling test. Clears the cached manifest directly
# (rather than reset(), which would re-resolve manifest_url from BB_ENV).
local_v2_manifest <- function(env = parent.frame()) {
  fixture <- tempfile(fileext = ".json")
  jsonlite::write_json(v2_manifest(), fixture, auto_unbox = TRUE)
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
  fixture
}

# Skip a test when the live manifest can't be fetched or isn't v2 yet. The v2
# prod/dev manifest is published by a separate Dagster job (Gate 0); until that
# runs, the live manifest is still v1 and the version gate raises.
skip_unless_live_v2 <- function() {
  bedrockbio:::reset()
  ok <- tryCatch(
    {
      bedrockbio:::get_manifest()
      TRUE
    },
    error = function(e) FALSE
  )
  if (!ok) {
    testthat::skip("live v2 manifest unavailable")
  }
}
