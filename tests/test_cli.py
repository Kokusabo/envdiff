from pathlib import Path

from typer.testing import CliRunner

from envdiff.cli import app

runner = CliRunner()


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_matching_files_exit_zero(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\nB=2\n")
    b = _write(tmp_path, "b.env", "A=9\nB=8\n")
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_missing_key_exits_one(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\nB=2\n")
    b = _write(tmp_path, "b.env", "A=1\n")
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 1
    assert "missing" in result.output
    assert "B" in result.output


def test_extra_key_exits_one(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\n")
    b = _write(tmp_path, "b.env", "A=1\nZ=5\n")
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 1
    assert "extra" in result.output


def test_empty_value_passes_without_strict(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\n")
    b = _write(tmp_path, "b.env", "A=\n")
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 0


def test_empty_value_fails_with_strict(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\n")
    b = _write(tmp_path, "b.env", "A=\n")
    result = runner.invoke(app, ["compare", str(a), str(b), "--strict"])
    assert result.exit_code == 1


def test_secrets_are_not_printed(tmp_path):
    a = _write(tmp_path, "a.env", "API_KEY=supersecretvalue\n")
    b = _write(tmp_path, "b.env", "")
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 1
    assert "supersecretvalue" not in result.output


def test_ignore_skips_keys(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\nDEBUG=true\n")
    b = _write(tmp_path, "b.env", "A=1\n")
    result = runner.invoke(app, ["compare", str(a), str(b), "-i", "DEBUG"])
    assert result.exit_code == 0


def test_json_output_has_no_values(tmp_path):
    import json

    a = _write(tmp_path, "a.env", "A=1\nAPI_KEY=supersecretvalue\n")
    b = _write(tmp_path, "b.env", "Z=zzz\n")
    result = runner.invoke(app, ["compare", str(a), str(b), "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["missing"] == ["A", "API_KEY"]
    assert payload["extra"] == ["Z"]
    assert "supersecretvalue" not in result.output


def test_json_ok_exits_zero(tmp_path):
    import json

    a = _write(tmp_path, "a.env", "A=1\n")
    b = _write(tmp_path, "b.env", "A=2\n")
    result = runner.invoke(app, ["compare", str(a), str(b), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["ok"] is True


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_multiple_others_exit_one_if_any_fails(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\n")
    ok = _write(tmp_path, "ok.env", "A=2\n")
    bad = _write(tmp_path, "bad.env", "")
    result = runner.invoke(app, ["compare", str(a), str(ok), str(bad)])
    assert result.exit_code == 1


def test_multiple_others_json_is_list(tmp_path):
    import json

    a = _write(tmp_path, "a.env", "A=1\n")
    ok = _write(tmp_path, "ok.env", "A=2\n")
    bad = _write(tmp_path, "bad.env", "")
    result = runner.invoke(app, ["compare", str(a), str(ok), str(bad), "--json"])
    payload = json.loads(result.output)
    assert isinstance(payload, list)
    assert [p["ok"] for p in payload] == [True, False]


def test_show_changed_masks_secrets(tmp_path):
    a = _write(tmp_path, "a.env", "API_KEY=oldsecretvalue\nLOG=info\n")
    b = _write(tmp_path, "b.env", "API_KEY=newsecretvalue\nLOG=debug\n")
    result = runner.invoke(app, ["compare", str(a), str(b), "--show-changed"])
    assert result.exit_code == 0
    assert "changed" in result.output
    assert "oldsecretvalue" not in result.output
    assert "newsecretvalue" not in result.output
    assert "debug" in result.output


def test_verbose_shows_parser_warnings(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\nBROKEN\n")
    b = _write(tmp_path, "b.env", "A=1\n")
    result = runner.invoke(app, ["compare", str(a), str(b), "--verbose"])
    assert "no '='" in result.output
    quiet = runner.invoke(app, ["compare", str(a), str(b)])
    assert "no '='" not in quiet.output
