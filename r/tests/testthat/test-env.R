test_that("default uses prod host", {
  old <- Sys.getenv("BB_ENV", unset = NA)
  on.exit({
    if (is.na(old)) Sys.unsetenv("BB_ENV") else Sys.setenv(BB_ENV = old)
    bedrockbio:::.onLoad(NULL, NULL)
  })
  Sys.unsetenv("BB_ENV")
  bedrockbio:::.onLoad(NULL, NULL)
  pkg <- bedrockbio:::pkg
  expect_equal(pkg$manifest_url, "https://data.bedrock.bio/manifest.json")
  expect_equal(pkg$credentials_url, "https://data.bedrock.bio/credentials.json")
})

test_that("BB_ENV=dev uses dev host", {
  old <- Sys.getenv("BB_ENV", unset = NA)
  on.exit({
    if (is.na(old)) Sys.unsetenv("BB_ENV") else Sys.setenv(BB_ENV = old)
    bedrockbio:::.onLoad(NULL, NULL)
  })
  Sys.setenv(BB_ENV = "dev")
  bedrockbio:::.onLoad(NULL, NULL)
  pkg <- bedrockbio:::pkg
  expect_equal(pkg$manifest_url, "https://data-dev.bedrock.bio/manifest.json")
  expect_equal(pkg$credentials_url, "https://data-dev.bedrock.bio/credentials.json")
})
