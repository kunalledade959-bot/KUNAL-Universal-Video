# Browser Worker v0.2

Target adapter: ShaheerTools at https://shaheertools.com/. Its current product page describes browser-only bulk generation, no signup/API key, 1000+ batch testing, character consistency, retry-failed and ZIP export. These are vendor claims, not runtime verification.

Current adapter can heuristically detect a prompt input and generation button, submit a batch, and stop on CAPTCHA/login/rate-limit indicators.

Not complete yet: result-image discovery, deterministic frame mapping, downloads, checksums and end-to-end browser verification. Do not call this production-ready until those are tested in a real browser.
