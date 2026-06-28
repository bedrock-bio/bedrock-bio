#' Describe a table: its context, columns, and partitions
#'
#' @param name Table identifier.
#' @returns A named list with `name`, `context`, `columns` (each with `name`,
#'   `type`, `description`, `nullable`), and `partitions` (a named list of
#'   partition column to `values` and `default`). Filter on partition columns
#'   for fastest reads.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' describe_table("ukb_ppp.pqtls")$name
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
