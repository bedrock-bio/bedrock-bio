#' List available tables, optionally filtered to one namespace
#'
#' @param namespace If given, return only that namespace's tables; otherwise
#'   all tables.
#' @returns A character vector of fully-qualified table identifiers.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' list_tables("ukb_ppp")
#' }
#'
#' @export
list_tables <- function(namespace = NULL) {
  if (is.null(namespace)) {
    return(names(get_manifest()))
  }

  namespaces <- get_namespaces()
  if (!namespace %in% names(namespaces)) {
    stop(
      "Namespace '", namespace, "' not found. ",
      "See list_namespaces() for available namespaces.",
      call. = FALSE
    )
  }
  namespaces[[namespace]]$tables
}
