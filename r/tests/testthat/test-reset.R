test_that("reset is exported", {
  expect_true("reset" %in% getNamespaceExports("bedrockbio"))
  expect_true(is.function(reset))
})

test_that("reset clears cached state", {
  pkg <- bedrockbio:::pkg
  pkg$manifest <- list("ns.tbl" = list())
  pkg$namespaces <- list(ns = list())
  bedrockbio:::reset()
  expect_null(pkg$manifest)
  expect_null(pkg$namespaces)
})
