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

local_manifest <- function(manifest, env = parent.frame()) {
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
  fixture
}

local_v2_manifest <- function(env = parent.frame()) {
  local_manifest(v2_manifest(), env)
}

clear_state <- function() {
  pkg <- bedrockbio:::pkg
  if (!is.null(pkg$conn)) {
    try(DBI::dbDisconnect(pkg$conn, shutdown = TRUE), silent = TRUE)
  }
  pkg$manifest <- NULL
  pkg$namespaces <- NULL
  pkg$conn <- NULL
  bedrockbio:::set_host_urls()
}

skip_unless_live_v2 <- function() {
  clear_state()
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
