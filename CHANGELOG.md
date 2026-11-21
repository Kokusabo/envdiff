# Changelog

## 0.2.0

### Added
- `envdiff scan`: find environment variables your code reads (Python, JS/TS,
  Go, Ruby, Rust, PHP) that are missing from `.env.example`, plus documented
  variables nothing reads.
- `envdiff example`: generate a `.env.example` from a real `.env`. Values are
  removed; `--keep-values` keeps only non-secret ones.
- `--format github` for `compare` and `scan`: errors show up inline on pull
  requests.
- GitHub Action (`uses: Kokusabo/envdiff@v0.2.0`) and pre-commit hooks.
- `compare` accepts several files, `--show-changed`, and `--verbose` parser
  warnings.

### Fixed
- Escaped quotes and backslashes inside double-quoted values (`"say \"hi\""`).
- A quoted value followed by a comment kept its quotes.
- A UTF-8 BOM broke the first key.
- Credentials inside URLs (`user:pass@`, `token@`) were printed in clear text.

## 0.1.0

- First release: `envdiff compare` with missing, extra and empty keys, secret
  masking, `--strict`, `--ignore`, and `--json`.
