#' Clear cached state (manifest, namespaces, and connection)
#'
#' The next call to a query function re-fetches the manifest and rebuilds the
#' connection. Useful when the manifest or `BB_ENV` has changed during a
#' long-running session.
#'
#' @returns Invisibly `NULL`.
#'
#' @examples
#' reset()
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
