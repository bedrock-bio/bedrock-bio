pkg <- new.env(parent = emptyenv())

.onLoad <- function(libname, pkgname) {
  pkg$catalog_url <- "https://data.bedrock.bio/manifest.json"
  pkg$credentials_url <- "https://data.bedrock.bio/credentials.json"
}

.onUnload <- function(libpath) {
  if (!is.null(pkg$conn)) {
    DBI::dbDisconnect(pkg$conn, shutdown = TRUE)
  }
}
