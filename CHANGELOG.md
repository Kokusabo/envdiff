# Changelog

## 0.1.0 (unreleased)

First release.

- `envdiff compare BASE OTHER...` reports missing, extra, and empty keys, with `--strict`, `--ignore`, `--json`, `--show-changed`, and `--verbose`.
- Secret values are masked by key name, and credentials inside URLs are masked for any key.
- Parser supports comments, `export`, single and double quotes with escapes, multiline quoted values, inline comments, BOM, and CRLF.
- Exit codes: `0` no problems, `1` differences found, `2` a file could not be read.
