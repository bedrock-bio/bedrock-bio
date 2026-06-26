#' Clear cached Bedrock Bio state
#'
#' Clears the cached manifest, namespaces, and database connection, and
#' re-resolves the data host from the `BB_ENV` environment variable. The next
#' call to a query function re-fetches the manifest and rebuilds the
#' connection. Useful when the manifest has changed, or `BB_ENV` has changed,
#' during a long-running session.
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
  pkg$conn <- NULL
  set_host_urls()
  invisible(NULL)
}
