pkg <- new.env(parent = emptyenv())

# Resolve the data host from BB_ENV and cache the derived URL. Called at load
# and again on reset() so a mid-session BB_ENV change takes effect.
set_host_urls <- function() {
  host <- if (identical(Sys.getenv("BB_ENV"), "dev")) {
    "https://data-dev.bedrock.bio"
  } else {
    "https://data.bedrock.bio"
  }
  pkg$manifest_url <- paste0(host, "/manifest.json")
}

.onLoad <- function(libname, pkgname) {
  set_host_urls()
}

.onUnload <- function(libpath) {
  if (!is.null(pkg$conn)) {
    DBI::dbDisconnect(pkg$conn, shutdown = TRUE)
  }
}
