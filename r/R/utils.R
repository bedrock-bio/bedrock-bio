fetch_json <- function(url) {
  h <- curl::new_handle()
  curl::handle_setheaders(h, "User-Agent" = "bedrock-bio")
  curl::handle_setopt(h, connecttimeout = 10, timeout = 10)
  con <- curl::curl(url, handle = h)
  on.exit(close(con))
  readLines(con, warn = FALSE)
}

manifest_version <- 2L

default_if_null <- function(x, default) if (is.null(x)) default else x

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

  raw_version <- as.integer(default_if_null(raw$version, NA))
  if (!identical(raw_version, manifest_version)) {
    stop(
      "Unsupported manifest version '", default_if_null(raw$version, "NULL"),
      "' at '", pkg$manifest_url, "'; this client requires version ",
      manifest_version, ". Upgrade bedrockbio to the latest release.",
      call. = FALSE
    )
  }

  manifest <- list()
  namespaces <- list()
  for (ns in names(raw$namespaces)) {
    ns_data <- raw$namespaces[[ns]]
    table_fqns <- paste0(ns, ".", names(ns_data$tables))

    for (i in seq_along(ns_data$tables)) {
      tbl <- ns_data$tables[[i]]
      manifest[[table_fqns[i]]] <- list(
        iceberg_json = tbl$iceberg_json,
        partitions = default_if_null(tbl$partitions, list()),
        columns = default_if_null(tbl$columns, list()),
        context = default_if_null(tbl$context, "")
      )
    }

    namespaces[[ns]] <- list(
      name = default_if_null(ns_data$name, ""),
      license = default_if_null(ns_data$license, ""),
      citation = default_if_null(ns_data$citation, ""),
      context = default_if_null(ns_data$context, ""),
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
get_connection <- function() {
  if (!is.null(pkg$conn)) {
    return(pkg$conn)
  }

  pkg$conn <- DBI::dbConnect(duckdb::duckdb())
  DBI::dbExecute(pkg$conn, "INSTALL httpfs")
  DBI::dbExecute(pkg$conn, "INSTALL iceberg")
  DBI::dbExecute(pkg$conn, "SET s3_endpoint='bedrock.bio'")
  DBI::dbExecute(pkg$conn, "SET s3_url_style='vhost'")
  DBI::dbExecute(pkg$conn, "SET s3_use_ssl=true")
  DBI::dbExecute(pkg$conn, "SET s3_region='auto'")

  pkg$conn
}
