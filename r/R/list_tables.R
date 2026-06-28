#' List available tables in the Bedrock Bio library
#'
#' @param namespace Optional namespace identifier (e.g., "ukb_ppp"). If given,
#'   only tables in that namespace are returned; if omitted, all tables across
#'   every namespace are returned.
#' @returns A character vector of fully-qualified table identifiers
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' list_tables()
#' list_tables("ukb_ppp")
#' }
#'
#' @export
list_tables <- function(namespace = NULL) {
  if (is.null(namespace)) {
    manifest <- get_manifest()
    return(names(manifest))
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
