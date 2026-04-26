#' Lazily query a table
#'
#' @param name Table identifier (e.g., "ukb_ppp.pqtls")
#' @param ... Required partition filters
#'   (e.g., ancestry = "EUR", protein_id = "A0FGR8")
#' @returns A lazy `tbl` backed by DuckDB, compatible with dplyr verbs.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' library(dplyr)
#'
#' df <- load_table(
#'   "dbsnp.vcf",
#'   assembly = "GRCh38",
#'   chromosome = "22"
#' ) |>
#'   select(rsid, position, ref_allele, alt_allele) |>
#'   head(5) |>
#'   collect()
#' }
#'
#' @export
load_table <- function(name, ...) {
  catalog <- get_catalog()

  if (!name %in% names(catalog)) {
    stop(
      "Table '", name, "' not found in catalog. ",
      "See list_tables() for available tables.",
      call. = FALSE
    )
  }

  entry <- catalog[[name]]
  filters <- list(...)
  required <- entry$required_filters
  allowed_values <- entry$allowed_values

  missing <- setdiff(required, names(filters))
  if (length(missing) > 0) {
    stop(
      "Missing required filters for '", name, "': ",
      paste(missing, collapse = ", "), ". ",
      "Required: ", paste(required, collapse = ", "), ".",
      call. = FALSE
    )
  }

  unknown <- setdiff(names(filters), required)
  if (length(unknown) > 0) {
    stop(
      "Unknown filters for '", name, "': ",
      paste(unknown, collapse = ", "), ". ",
      "Valid filters: ", paste(required, collapse = ", "), ".",
      call. = FALSE
    )
  }

  for (col in names(filters)) {
    val <- trimws(as.character(filters[[col]]))
    if (col %in% names(allowed_values)) {
      allowed <- allowed_values[[col]]
      if (val %in% allowed) {
        filters[[col]] <- val
      } else {
        match_idx <- match(tolower(val), tolower(allowed))
        if (!is.na(match_idx)) {
          filters[[col]] <- allowed[match_idx]
        } else {
          stop(
            "Invalid value '", val, "' for filter '", col, "'. ",
            "Allowed: ", paste(allowed, collapse = ", "), ".",
            call. = FALSE
          )
        }
      }
    } else {
      filters[[col]] <- val
    }
  }

  conn <- get_connection()

  where_parts <- vapply(names(filters), function(col) {
    quoted <- DBI::dbQuoteString(conn, filters[[col]])
    sprintf("%s = %s", col, quoted)
  }, character(1))

  query <- sprintf("SELECT * FROM iceberg_scan('%s')", entry$metadata_json)
  if (length(where_parts) > 0) {
    query <- paste(query, "WHERE", paste(where_parts, collapse = " AND "))
  }

  dplyr::tbl(conn, dplyr::sql(query))
}
