pkg <- new.env(parent = emptyenv())

.onLoad <- function(libname, pkgname) {
  host <- if (identical(Sys.getenv("BB_ENV"), "dev")) {
    "https://data-dev.bedrock.bio"
  } else {
    "https://data.bedrock.bio"
  }
  pkg$manifest_url <- paste0(host, "/manifest.json")
  pkg$credentials_url <- paste0(host, "/credentials.json")
}

.onUnload <- function(libpath) {
  if (!is.null(pkg$conn)) {
    DBI::dbDisconnect(pkg$conn, shutdown = TRUE)
  }
}
