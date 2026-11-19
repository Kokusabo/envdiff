from envdiff.parser import parse_env


def test_basic_pairs():
    assert parse_env("A=1\nB=two") == {"A": "1", "B": "two"}


def test_ignores_comments_and_blank_lines():
    text = "# comment\n\nA=1\n   # indented comment\n"
    assert parse_env(text) == {"A": "1"}


def test_export_prefix():
    assert parse_env("export TOKEN=abc") == {"TOKEN": "abc"}


def test_quoted_values():
    text = 'A="hello world"\nB=\'single\'\nC="line\\nbreak"'
    assert parse_env(text) == {"A": "hello world", "B": "single", "C": "line\nbreak"}


def test_inline_comment_on_unquoted_value():
    assert parse_env("A=value # note") == {"A": "value"}


def test_hash_inside_quotes_is_kept():
    assert parse_env('A="x # not a comment"') == {"A": "x # not a comment"}


def test_empty_value_is_kept():
    assert parse_env("EMPTY=") == {"EMPTY": ""}


def test_value_with_equals_sign():
    assert parse_env("URL=postgres://u:p@h/db?x=1") == {"URL": "postgres://u:p@h/db?x=1"}


def test_duplicate_key_last_wins():
    assert parse_env("A=1\nA=2") == {"A": "2"}


def test_lines_without_equals_are_skipped():
    assert parse_env("NOT_A_PAIR\nA=1") == {"A": "1"}
