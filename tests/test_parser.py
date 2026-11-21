from envdiff.parser import parse_env, parse_env_detailed


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


def test_quoted_value_with_trailing_comment():
    assert parse_env('A="x" # note') == {"A": "x"}
    assert parse_env("B='y' # note") == {"B": "y"}


def test_bom_is_stripped_from_first_key():
    assert parse_env("﻿FIRST=1\nSECOND=2") == {"FIRST": "1", "SECOND": "2"}


def test_crlf_line_endings():
    assert parse_env("A=1\r\nB=2\r\n") == {"A": "1", "B": "2"}


def test_warning_for_line_without_equals():
    detailed = parse_env_detailed("GOOD=1\nBROKEN LINE\n")
    assert detailed.values == {"GOOD": "1"}
    assert any("line 2" in w for w in detailed.warnings)


def test_warning_for_invalid_key_with_space():
    detailed = parse_env_detailed("BAD KEY=1")
    assert detailed.values == {}
    assert any("invalid key" in w for w in detailed.warnings)


def test_warning_for_duplicate_key():
    detailed = parse_env_detailed("A=1\nA=2")
    assert detailed.values == {"A": "2"}
    assert any("already defined on line 1" in w for w in detailed.warnings)


def test_no_warnings_for_clean_file():
    assert parse_env_detailed("A=1\n# c\n").warnings == []


def test_escaped_quotes_and_backslashes_in_double_quotes():
    assert parse_env(r'A="say \"hi\""') == {"A": 'say "hi"'}
    assert parse_env(r'B="C:\\path\\to"') == {"B": r"C:\path\to"}
    assert parse_env(r'C="tab\there"') == {"C": "tab\there"}
    # Unknown escapes keep the backslash.
    assert parse_env(r'D="C:\path"') == {"D": r"C:\path"}


def test_single_quotes_are_literal():
    assert parse_env(r"A='no \n escape'") == {"A": r"no \n escape"}


def test_unclosed_quote_is_kept_as_is():
    assert parse_env('A="open') == {"A": '"open'}
