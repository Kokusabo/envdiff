# envdiff

[![CI](https://github.com/Kokusabo/envdiff/actions/workflows/ci.yml/badge.svg)](https://github.com/Kokusabo/envdiff/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Keep `.env` files honest.** envdiff catches the config bugs that only show up in production:

- a variable your code reads but nobody added to `.env.example`
- a key that exists in `.env.example` but is missing from `.env.prod`
- a secret that would have been printed in a CI log

It never prints secret values, and every command returns a non-zero exit code on problems, so it drops straight into CI.

```console
$ envdiff scan src --against .env.example
                      code vs .env.example
+--------------------------------------------------------------+
| Variable        | Status       | Where                       |
|-----------------+--------------+-----------------------------|
| FEATURE_FLAGS   | undocumented | src/client.ts:3             |
| MAILGUN_API_KEY | undocumented | src/settings.py:10          |
| LOG_LEVEL       | unused       | .env.example                |
+--------------------------------------------------------------+
2 undocumented, 1 unused (9 variables read by the code)
```

## Install

```bash
pip install git+https://github.com/Kokusabo/envdiff.git
```

Python 3.11+. Works on Linux, macOS, and Windows.

## Commands

### `envdiff scan` — find undocumented variables in your code

```bash
envdiff scan                        # scan the current folder against .env.example
envdiff scan src api -a .env.example
envdiff scan --strict               # also fail on documented variables nothing reads
```

Understands:

| Language | Patterns |
|---|---|
| Python | `os.getenv("X")`, `os.environ["X"]`, `os.environ.get("X")` |
| JavaScript / TypeScript | `process.env.X`, `process.env["X"]`, `import.meta.env.X` |
| Go | `os.Getenv("X")`, `os.LookupEnv("X")` |
| Ruby | `ENV["X"]`, `ENV.fetch("X")` |
| Rust | `env::var("X")`, `env::var_os("X")` |
| PHP | `getenv("X")` |

`node_modules`, virtualenvs, and build folders are skipped. Runtime variables such as `PATH`, `HOME`, `NODE_ENV`, and Vite's `MODE`/`DEV`/`PROD` are ignored; add more with `-i NAME`.

### `envdiff compare` — check env files against a reference

```console
$ envdiff compare .env.example .env.prod
                  .env.example vs .env.prod
+------------------------------------------------------------+
| Key       | Status  | .env.example             | .env.prod |
|-----------+---------+--------------------------+-----------|
| REDIS_URL | missing | redis://localhost:6379/0 | -         |
| CACHE_TTL | extra   | -                        | 300       |
+------------------------------------------------------------+
1 missing, 1 extra, 0 empty
```

```bash
envdiff compare .env.example .env.staging .env.prod   # several files at once
envdiff compare BASE OTHER --strict                   # also fail on empty values
envdiff compare BASE OTHER --show-changed             # list keys whose values differ
envdiff compare BASE OTHER -i DEBUG -i LOG_LEVEL      # skip keys
envdiff compare BASE OTHER -v                         # warn about bad lines and duplicates
```

### `envdiff example` — generate `.env.example` from `.env`

```bash
envdiff example .env                       # print a template with values removed
envdiff example .env -o .env.example       # write it (use --force to overwrite)
envdiff example .env --keep-values         # keep non-secret values like PORT=8000
```

Comments and blank lines are kept. Secrets and URLs with credentials are always blanked.

## Use in CI

### GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: Kokusabo/envdiff@v0.2.0
  with:
    args: scan src --against .env.example
```

Problems show up as inline annotations on the pull request, pointing at the exact line.

### Any CI

```bash
pip install git+https://github.com/Kokusabo/envdiff.git
envdiff scan --format github      # or --json for your own tooling
```

### pre-commit

```yaml
repos:
  - repo: https://github.com/Kokusabo/envdiff
    rev: v0.2.0
    hooks:
      - id: envdiff-scan
```

## Output formats

Every check supports `--format table` (default), `--format json` (or `--json`), and `--format github`. JSON output contains key names and file locations only, never values.

## Secret masking

- Keys containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PRIVATE`, `CREDENTIAL`, `DSN`, or `AUTH` are shown as `********`.
- Credentials inside URLs are masked for every key: `postgres://app:********@db/shop`, `https://********@sentry.io/1`.

## Supported `.env` syntax

Comments, blank lines, `export KEY=value`, single quotes (literal), double quotes with `\"`, `\\`, `\n`, `\t` escapes, a comment after a quoted value, inline comments on unquoted values, empty values, UTF-8 BOM, and Windows (CRLF) line endings.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | No problems |
| 1 | Problems found |
| 2 | Usage error (bad arguments, missing file, refusing to overwrite) |

## Development

```bash
git clone https://github.com/Kokusabo/envdiff.git
cd envdiff
pip install -e ".[dev]"
pytest
ruff check .
```

Try it on the demo project in [`examples/`](examples):

```bash
envdiff scan examples/app -a examples/.env.example
envdiff compare examples/.env.example examples/.env.staging examples/.env.prod --show-changed -v
```

See [CHANGELOG.md](CHANGELOG.md) for what changed between versions.

## License

MIT. See [LICENSE](LICENSE).
