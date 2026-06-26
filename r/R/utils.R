fetch_json <- function(url) {
  h <- curl::new_handle()
  curl::handle_setheaders(h, "User-Agent" = "bedrock-bio")
  # Bound network stalls on the manifest fetch (seconds).
  curl::handle_setopt(h, connecttimeout = 10, timeout = 10)
  con <- curl::curl(url, handle = h)
  on.exit(close(con))
  readLines(con, warn = FALSE)
}

column_fields <- c("name", "type", "description", "nullable", "allowed_values")

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
        description = default_if_null(meta$description, ""),
        citation = ns_data$citation,
        source_url = default_if_null(ns_data$source_url, ""),
        license = default_if_null(ns_data$license, ""),
        columns = lapply(
          meta$columns,
          function(col) col[intersect(column_fields, names(col))]
        )
      )
    }

    namespaces[[ns]] <- list(
      id = ns,
      name = default_if_null(ns_data$name, ""),
      description = default_if_null(ns_data$description, ""),
      source_url = default_if_null(ns_data$source_url, ""),
      license = default_if_null(ns_data$license, ""),
      instructions = default_if_null(ns_data$instructions, ""),
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
get_connection <- function() {
  if (!is.null(pkg$conn)) {
    return(pkg$conn)
  }

  pkg$conn <- DBI::dbConnect(duckdb::duckdb())
  DBI::dbExecute(pkg$conn, "INSTALL httpfs")
  DBI::dbExecute(pkg$conn, "INSTALL iceberg")
  # Anonymous, cache-fronted reads over the public custom domain. metadata_json
  # is s3://<bucket>/...; vhost maps it to https://<bucket>.bedrock.bio/... —
  # no credentials, no S3 API. The connection is private to this package.
  DBI::dbExecute(pkg$conn, "SET s3_endpoint='bedrock.bio'")
  DBI::dbExecute(pkg$conn, "SET s3_url_style='vhost'")
  DBI::dbExecute(pkg$conn, "SET s3_use_ssl=true")
  DBI::dbExecute(pkg$conn, "SET s3_region='auto'")

  pkg$conn
}
