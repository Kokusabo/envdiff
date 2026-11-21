from envdiff.example import make_example
from envdiff.parser import parse_env

SOURCE = """# App settings
APP_NAME=shop
DEBUG=true

# Secrets
API_KEY=abc123
DATABASE_URL=postgres://app:pw@db:5432/shop
GREETING="hello world"
BROKEN LINE
APP_NAME=duplicate
"""


def test_values_are_removed_by_default():
    out = make_example(SOURCE)
    assert parse_env(out) == {
        "APP_NAME": "",
        "DEBUG": "",
        "API_KEY": "",
        "DATABASE_URL": "",
        "GREETING": "",
    }


def test_comments_and_blank_lines_are_kept():
    out = make_example(SOURCE)
    assert out.startswith("# App settings\nAPP_NAME=\n")
    assert "\n\n# Secrets\n" in out


def test_broken_and_duplicate_lines_are_dropped():
    out = make_example(SOURCE)
    assert "BROKEN" not in out
    assert out.count("APP_NAME=") == 1


def test_keep_values_keeps_only_safe_values():
    env = parse_env(make_example(SOURCE, keep_values=True))
    assert env["APP_NAME"] == "shop"
    assert env["DEBUG"] == "true"
    assert env["GREETING"] == "hello world"
    assert env["API_KEY"] == ""
    assert env["DATABASE_URL"] == ""


def test_round_trip_keeps_tricky_values():
    source = 'A="has # hash"\nB="say \\"hi\\""\n'
    assert parse_env(make_example(source, keep_values=True)) == parse_env(source)


def test_keep_values_drops_url_tokens():
    env = parse_env(make_example("HOOK_URL=https://tok123@hooks.example.com/x\n", keep_values=True))
    assert env["HOOK_URL"] == ""
