#' List available namespaces (data sources) in the Bedrock Bio library
#'
#' @returns A character vector of namespace identifiers
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' list_namespaces()
#' }
#'
#' @export
list_namespaces <- function() {
  namespaces <- get_namespaces()
  names(namespaces)
}
