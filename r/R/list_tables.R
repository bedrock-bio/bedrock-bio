#' List available tables in the Bedrock Bio library
#'
#' @returns A character vector of table identifiers
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' list_tables()
#' }
#'
#' @export
list_tables <- function() {
  catalog <- get_catalog()
  names(catalog)
}
