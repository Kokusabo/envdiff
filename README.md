# envdiff

[![CI](https://github.com/YOUR_USERNAME/envdiff/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/envdiff/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Compare `.env` files and find **missing**, **extra**, and **empty** variables before they break production. Secret values are masked in the output, and the exit code makes it easy to use in CI.

```console
$ envdiff compare examples/.env.example examples/.env.prod
                  .env.example vs .env.prod
+------------------------------------------------------------+
| Key       | Status  | .env.example             | .env.prod |
|-----------+---------+--------------------------+-----------|
| REDIS_URL | missing | redis://localhost:6379/0 | -         |
| CACHE_TTL | extra   | -                        | 300       |
+------------------------------------------------------------+
1 missing, 1 extra, 0 empty
```

## Why

Config drift is a classic source of "works on my machine" and "it broke in prod". `.env.example` says what the app needs. `envdiff` checks that a real environment file matches it, and it never prints your secrets.

## Install

```bash
pip install envdiff
```

Or from source:

```bash
git clone https://github.com/YOUR_USERNAME/envdiff.git
cd envdiff
pip install -e ".[dev]"
```

## Usage

```bash
envdiff compare BASE OTHER           # report missing and extra keys
envdiff compare BASE OTHER --strict  # also fail on empty values
envdiff compare BASE OTHER -i DEBUG -i LOG_LEVEL  # skip keys (repeatable)
envdiff compare BASE OTHER --json    # machine-readable output, never includes values
envdiff --version
```

- `BASE` is the reference, usually `.env.example`.
- `OTHER` is the file to check, such as `.env.prod`.
- Exit code `0` means no problems were found. `1` means there are differences.
- Keys whose names contain `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, and similar are shown as `********`.

CI example:

```yaml
- run: envdiff compare .env.example .env.production --strict
```

## Supported syntax

Comments (`#`), blank lines, `export KEY=value`, single and double quoted values, inline comments on unquoted values, and empty values.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## License

MIT. See [LICENSE](LICENSE).
