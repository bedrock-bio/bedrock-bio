#' Describe a table's metadata, citation, and columns
#'
#' @param name Table identifier (e.g., "ukb_ppp.pqtls")
#' @returns A named list with name, description, citation, source_url,
#'   license, and columns.
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
  catalog <- get_catalog()

  if (!name %in% names(catalog)) {
    stop(
      "Table '", name, "' not found in catalog. ",
      "See list_tables() for available tables.",
      call. = FALSE
    )
  }

  entry <- catalog[[name]]
  list(
    name = name,
    description = entry$description,
    citation = entry$citation,
    source_url = entry$source_url,
    license = entry$license,
    columns = entry$columns
  )
}
