#' Clear cached Bedrock Bio state
#'
#' Clears the cached manifest, namespaces, credentials, and database
#' connection, and re-resolves the data host from the `BB_ENV` environment
#' variable. The next call to a query function re-fetches the manifest and
#' credentials and rebuilds the connection. Useful when credentials have been
#' rotated, or `BB_ENV` has changed, during a long-running session.
#'
#' @returns Invisibly `NULL`.
#'
#' @examples
#' \dontrun{
#' library(bedrockbio)
#' reset()
#' }
#'
#' @export
reset <- function() {
  if (!is.null(pkg$conn)) {
    try(DBI::dbDisconnect(pkg$conn, shutdown = TRUE), silent = TRUE)
  }
  pkg$manifest <- NULL
  pkg$namespaces <- NULL
  pkg$credentials <- NULL
  pkg$conn <- NULL
  set_host_urls()
  invisible(NULL)
}
