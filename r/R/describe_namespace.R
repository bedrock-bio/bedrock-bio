#' Describe a namespace's metadata, citation, license, and tables
#'
#' @param name Namespace identifier (e.g., "ukb_ppp")
#' @returns A named list with id, name, description, source_url, license,
#'   instructions, citation, and tables (character vector of fully-qualified
#'   table identifiers). Use `describe_table()` for per-table details.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' info <- describe_namespace("ukb_ppp")
#' info$tables
#' }
#'
#' @export
describe_namespace <- function(name) {
  namespaces <- get_namespaces()

  if (!name %in% names(namespaces)) {
    stop(
      "Namespace '", name, "' not found. ",
      "See list_namespaces() for available namespaces.",
      call. = FALSE
    )
  }

  namespaces[[name]]
}
