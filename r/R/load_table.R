#' Lazily query a table
#'
#' @param name Table identifier.
#' @returns A lazy `tbl` backed by DuckDB, compatible with dplyr verbs. Filter
#'   on partition columns (see `describe_table()`) for fastest reads.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' library(dplyr)
#'
#' load_table("dbsnp.vcf") |>
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

  conn <- get_connection()
  query <- DBI::sqlInterpolate(
    conn,
    "SELECT * FROM iceberg_scan(?path)",
    path = manifest[[name]]$iceberg_json
  )
  dplyr::tbl(conn, dplyr::sql(query))
}
