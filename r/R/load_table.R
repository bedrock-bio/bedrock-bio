#' Lazily query a table
#'
#' @param name Table identifier (e.g., "ukb_ppp.pqtls")
#' @returns A lazy `tbl` backed by DuckDB, compatible with dplyr verbs.
#'   Use `describe_table()` to see partition columns and their allowed
#'   values; filter on partition columns for fastest reads.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' library(dplyr)
#'
#' df <- load_table("dbsnp.vcf") |>
#'   filter(assembly == "GRCh38", chromosome == "22") |>
#'   select(rsid, position, ref_allele, alt_allele) |>
#'   head(5) |>
#'   collect()
#' }
#'
#' @export
load_table <- function(name) {
  manifest <- get_manifest()

  if (!name %in% names(manifest)) {
    stop(
      "Table '", name, "' not found in manifest. ",
      "See list_tables() for available tables.",
      call. = FALSE
    )
  }

  entry <- manifest[[name]]
  conn <- get_connection()
  query <- DBI::sqlInterpolate(
    conn,
    "SELECT * FROM iceberg_scan(?path)",
    path = entry$iceberg_json
  )
  dplyr::tbl(conn, dplyr::sql(query))
}
