fetch_json <- function(url) {
  h <- curl::new_handle()
  curl::handle_setheaders(h, "User-Agent" = "bedrock-bio")
  # Bound network stalls on the manifest/credentials fetches (seconds).
  curl::handle_setopt(h, connecttimeout = 10, timeout = 10)
  con <- curl::curl(url, handle = h)
  on.exit(close(con))
  readLines(con, warn = FALSE)
}

column_fields <- c("name", "type", "description", "nullable", "allowed_values")

#' @noRd
load_manifest <- function() {
  if (!is.null(pkg$manifest)) return(invisible(NULL))

  raw <- tryCatch(
    jsonlite::fromJSON(fetch_json(pkg$manifest_url), simplifyDataFrame = FALSE),
    error = function(e) {
      stop(
        "Unable to access manifest URL '", pkg$manifest_url, "'",
        call. = FALSE
      )
    }
  )

  manifest <- list()
  namespaces <- list()
  for (ns in names(raw$namespaces)) {
    ns_data <- raw$namespaces[[ns]]
    table_fqns <- paste0(ns, ".", names(ns_data$tables))

    for (i in seq_along(ns_data$tables)) {
      meta <- ns_data$tables[[i]]
      manifest[[table_fqns[i]]] <- list(
        metadata_json = meta$metadata_json,
        partition_by = as.character(meta$partition_by),
        sort_by = as.character(meta$sort_by),
        description = meta$description,
        citation = ns_data$citation,
        source_url = ns_data$source_url,
        license = ns_data$license,
        columns = lapply(
          meta$columns,
          function(col) col[intersect(names(col), column_fields)]
        )
      )
    }

    namespaces[[ns]] <- list(
      id = ns,
      name = ns_data$name,
      description = ns_data$description,
      source_url = ns_data$source_url,
      license = ns_data$license,
      instructions = ns_data$instructions,
      citation = ns_data$citation,
      tables = table_fqns
    )
  }
  pkg$manifest <- manifest
  pkg$namespaces <- namespaces
  invisible(NULL)
}

#' @noRd
get_manifest <- function() {
  load_manifest()
  pkg$manifest
}

#' @noRd
get_namespaces <- function() {
  load_manifest()
  pkg$namespaces
}

#' @noRd
get_credentials <- function() {
  if (!is.null(pkg$credentials)) {
    return(pkg$credentials)
  }

  pkg$credentials <- tryCatch(
    jsonlite::fromJSON(fetch_json(pkg$credentials_url)),
    error = function(e) {
      stop(
        "Unable to access credentials URL '", pkg$credentials_url, "'",
        call. = FALSE
      )
    }
  )
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

  DBI::dbExecute(
    pkg$conn,
    "CREATE SECRET (TYPE s3, KEY_ID ?, SECRET ?, ENDPOINT ?, URL_STYLE 'path')",
    params = list(
      credentials$R2_ACCESS_KEY_ID,
      credentials$R2_SECRET_ACCESS_KEY,
      paste0(credentials$R2_ACCOUNT_ID, ".r2.cloudflarestorage.com")
    )
  )

  pkg$conn
}
