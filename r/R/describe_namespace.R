#' Describe a namespace: its name, citation, license, context, and tables
#'
#' @param name Namespace identifier.
#' @returns A named list with `name`, `citation`, `license`, `context`, and
#'   `tables` (fully-qualified table identifiers). Use `describe_table()` for
#'   per-table details.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' describe_namespace("ukb_ppp")$tables
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
