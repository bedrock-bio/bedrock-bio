#' List available namespaces (data sources)
#'
#' @returns A character vector of namespace identifiers.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' list_namespaces()
#' }
#'
#' @export
list_namespaces <- function() {
  names(get_namespaces())
}
