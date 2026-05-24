fetch_json <- function(url) {
  h <- curl::new_handle()
  curl::handle_setheaders(h, "User-Agent" = "bedrock-bio")
  con <- curl::curl(url, handle = h)
  on.exit(close(con))
  readLines(con, warn = FALSE)
}

column_fields <- c("name", "type", "description", "nullable", "allowed_values")

#' @noRd
load_manifest <- function() {
  if (!is.null(pkg$catalog)) return(invisible(NULL))

  raw <- tryCatch(
    jsonlite::fromJSON(fetch_json(pkg$catalog_url), simplifyDataFrame = FALSE),
    error = function(e) {
      stop(
        "Unable to access manifest URL '", pkg$catalog_url, "'. ",
        "Check internet connection and try again.",
        call. = FALSE
      )
    }
  )

  catalog <- list()
  namespaces <- list()
  for (ns in names(raw$namespaces)) {
    ns_data <- raw$namespaces[[ns]]
    table_fqns <- paste0(ns, ".", names(ns_data$tables))

    for (i in seq_along(ns_data$tables)) {
      meta <- ns_data$tables[[i]]
      catalog[[table_fqns[i]]] <- list(
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
  pkg$catalog <- catalog
  pkg$namespaces <- namespaces
  invisible(NULL)
}

#' @noRd
get_catalog <- function() {
  load_manifest()
  pkg$catalog
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
        "Unable to fetch credentials from '", pkg$credentials_url, "'. ",
        "Check internet connection and try again.",
        call. = FALSE
      )
    }
  )
  pkg$credentials
}

#' @noRd
reset <- function() {
  if (!is.null(pkg$conn)) {
    try(DBI::dbDisconnect(pkg$conn, shutdown = TRUE), silent = TRUE)
  }
  pkg$catalog <- NULL
  pkg$namespaces <- NULL
  pkg$credentials <- NULL
  pkg$conn <- NULL
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
