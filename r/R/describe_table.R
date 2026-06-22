#' Describe a table's metadata, citation, and columns
#'
#' @param name Table identifier (e.g., "ukb_ppp.pqtls")
#' @returns A named list with name, description, citation, source_url,
#'   license, partition_by, sort_by, and columns.
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
    description = entry$description,
    citation = entry$citation,
    source_url = entry$source_url,
    license = entry$license,
    partition_by = entry$partition_by,
    sort_by = entry$sort_by,
    columns = entry$columns
  )
}
