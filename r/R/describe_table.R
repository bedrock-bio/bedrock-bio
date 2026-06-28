#' Describe a table: its context, columns, and partitions
#'
#' @param name Table identifier (e.g., "ukb_ppp.pqtls")
#' @returns A named list with `name`, `context` (prose: what the table is, how
#'   to query it, sort/related-table hints), `columns` (each a list of
#'   `name`, `type`, `description`, `nullable`), and `partitions` (a named list
#'   of partition column to `values` and `default`).
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' info <- describe_table("ukb_ppp.pqtls")
#' info$name
#' }
#'
#' @export
describe_table <- function(name) {
  manifest <- get_manifest()

  if (!name %in% names(manifest)) {
    stop(
      "Table '", name, "' not found in manifest. ",
      "See list_tables() for available tables.",
      call. = FALSE
    )
  }

  entry <- manifest[[name]]
  list(
    name = name,
    context = entry$context,
    columns = entry$columns,
    partitions = entry$partitions
  )
}
