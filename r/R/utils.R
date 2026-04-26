fetch_json <- function(url) {
  h <- curl::new_handle()
  curl::handle_setheaders(h, "User-Agent" = "bedrock-bio")
  con <- curl::curl(url, handle = h)
  on.exit(close(con))
  readLines(con, warn = FALSE)
}

#' @noRd
get_catalog <- function() {
  if (!is.null(pkg$catalog)) {
    return(pkg$catalog)
  }

  raw <- tryCatch(
    jsonlite::fromJSON(fetch_json(pkg$catalog_url), simplifyDataFrame = FALSE),
    error = function(e) {
      stop(
        "Unable to access catalog URL '", pkg$catalog_url, "'. ",
        "Check internet connection and try again.",
        call. = FALSE
      )
    }
  )

  entries <- list()
  for (ns in names(raw$namespaces)) {
    tables <- raw$namespaces[[ns]]$tables
    for (table_name in names(tables)) {
      meta <- tables[[table_name]]
      partition_by <- meta$partition_by
      if (is.null(partition_by)) partition_by <- character(0)
      required_filters <- partition_by[partition_by != "partition"]

      allowed_values <- list()
      if (length(required_filters) > 0 && length(meta$columns) > 0) {
        col_names <- vapply(meta$columns, function(c) c$name, character(1))
        for (f in required_filters) {
          idx <- match(f, col_names)
          if (!is.na(idx) && !is.null(meta$columns[[idx]]$allowed_values)) {
            av <- meta$columns[[idx]]$allowed_values
            allowed_values[[f]] <- as.character(av)
          }
        }
      }

      keep <- c(
        "name", "type", "description",
        "nullable", "allowed_values"
      )
      columns <- lapply(meta$columns, function(col) {
        col[intersect(names(col), keep)]
      })

      ns_data <- raw$namespaces[[ns]]
      entries[[paste0(ns, ".", table_name)]] <- list(
        metadata_json = meta$metadata_json,
        required_filters = required_filters,
        allowed_values = allowed_values,
        description = meta$description,
        citation = ns_data$citation,
        source_url = ns_data$source_url,
        license = ns_data$license,
        columns = columns
      )
    }
  }
  pkg$catalog <- entries
  pkg$catalog
}

#' @noRd
get_credentials <- function() {
  if (!is.null(pkg$credentials)) {
    return(pkg$credentials)
  }

  override_credentials <- list(
    BB_R2_ACCOUNT_ID = Sys.getenv("BB_R2_ACCOUNT_ID"),
    BB_R2_ACCESS_KEY_ID = Sys.getenv("BB_R2_ACCESS_KEY_ID"),
    BB_R2_SECRET_ACCESS_KEY = Sys.getenv("BB_R2_SECRET_ACCESS_KEY")
  )

  pkg$credentials <- if (all(nzchar(override_credentials))) {
    override_credentials
  } else {
    tryCatch(
      jsonlite::fromJSON(fetch_json(pkg$credentials_url)),
      error = function(e) {
        stop(
          "Unable to fetch credentials from '", pkg$credentials_url, "'. ",
          "Check internet connection and try again.",
          call. = FALSE
        )
      }
    )
  }
  pkg$credentials
}

#' @noRd
get_connection <- function() {
  if (!is.null(pkg$conn)) {
    return(pkg$conn)
  }

  credentials <- get_credentials()
  pkg$conn <- DBI::dbConnect(duckdb::duckdb())
  DBI::dbExecute(pkg$conn, "INSTALL httpfs")
  DBI::dbExecute(pkg$conn, "INSTALL iceberg")

  DBI::dbExecute(pkg$conn, sprintf(
    "CREATE SECRET (
      TYPE s3,
      KEY_ID '%s',
      SECRET '%s',
      ENDPOINT '%s.r2.cloudflarestorage.com',
      URL_STYLE 'path'
    )",
    credentials$BB_R2_ACCESS_KEY_ID,
    credentials$BB_R2_SECRET_ACCESS_KEY,
    credentials$BB_R2_ACCOUNT_ID
  ))

  pkg$conn
}
