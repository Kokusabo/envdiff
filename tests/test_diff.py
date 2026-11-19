from envdiff.diff import compare
from envdiff.redact import display_value, is_secret_key


def test_identical_envs_have_no_issues():
    result = compare({"A": "1"}, {"A": "2"})
    assert not result.has_issues


def test_missing_key():
    result = compare({"A": "1", "B": "2"}, {"A": "1"})
    assert result.missing == ["B"]
    assert result.has_errors


def test_extra_key():
    result = compare({"A": "1"}, {"A": "1", "C": "3"})
    assert result.extra == ["C"]
    assert result.has_errors


def test_empty_value_is_warning_not_error():
    result = compare({"A": "1"}, {"A": ""})
    assert result.empty == ["A"]
    assert not result.has_errors
    assert result.has_issues


def test_secret_detection():
    assert is_secret_key("DATABASE_PASSWORD")
    assert is_secret_key("api_token")
    assert is_secret_key("STRIPE_SECRET_KEY")
    assert not is_secret_key("DEBUG")


def test_display_masks_secrets_only():
    assert display_value("API_KEY", "abc123") == "********"
    assert display_value("LOG_LEVEL", "info") == "info"
    assert display_value("LOG_LEVEL", "") == "(empty)"
