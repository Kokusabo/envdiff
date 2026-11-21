from pathlib import Path

from typer.testing import CliRunner

from envdiff import __version__
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
    assert __version__ in result.output


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


def test_github_format_prints_annotations(tmp_path):
    a = _write(tmp_path, "a.env", "A=1\nB=2\n")
    b = _write(tmp_path, "b.env", "A=1\nC=3\n")
    result = runner.invoke(app, ["compare", str(a), str(b), "--format", "github"])
    assert result.exit_code == 1
    assert "::error file=" in result.output
    assert "B is missing" in result.output
    assert "C is not defined in a.env" in result.output


def test_example_prints_template(tmp_path):
    src = _write(tmp_path, ".env", "# db\nAPI_KEY=secret\nPORT=8000\n")
    result = runner.invoke(app, ["example", str(src)])
    assert result.exit_code == 0
    assert result.output == "# db\nAPI_KEY=\nPORT=\n"


def test_example_refuses_to_overwrite(tmp_path):
    src = _write(tmp_path, ".env", "A=1\n")
    out = _write(tmp_path, ".env.example", "KEEP=me\n")
    result = runner.invoke(app, ["example", str(src), "-o", str(out)])
    assert result.exit_code == 2
    assert out.read_text(encoding="utf-8") == "KEEP=me\n"
    forced = runner.invoke(app, ["example", str(src), "-o", str(out), "--force"])
    assert forced.exit_code == 0
    assert out.read_text(encoding="utf-8") == "A=\n"


def _scan_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text(
        'import os\nDB = os.getenv("DATABASE_URL")\nKEY = os.environ["NEW_SECRET"]\n'
        'MODE = os.getenv("NODE_ENV")\n',
        encoding="utf-8",
    )
    example = _write(tmp_path, ".env.example", "DATABASE_URL=\nOLD_UNUSED=\n")
    return src, example


def test_scan_finds_undocumented_variables(tmp_path):
    src, example = _scan_project(tmp_path)
    result = runner.invoke(app, ["scan", str(src), "--against", str(example)])
    assert result.exit_code == 1
    assert "NEW_SECRET" in result.output
    assert "undocumented" in result.output
    assert "OLD_UNUSED" in result.output
    assert "NODE_ENV" not in result.output  # ignored by default


def test_scan_json_and_strict(tmp_path):
    import json

    src, example = _scan_project(tmp_path)
    result = runner.invoke(app, ["scan", str(src), "-a", str(example), "--json"])
    payload = json.loads(result.output)
    assert list(payload["undocumented"]) == ["NEW_SECRET"]
    assert payload["undocumented"]["NEW_SECRET"][0]["line"] == 3
    assert payload["unused"] == ["OLD_UNUSED"]

    ok = runner.invoke(app, ["scan", str(src), "-a", str(example), "-i", "NEW_SECRET"])
    assert ok.exit_code == 0
    strict = runner.invoke(
        app, ["scan", str(src), "-a", str(example), "-i", "NEW_SECRET", "--strict"]
    )
    assert strict.exit_code == 1


def test_scan_github_annotations_point_to_source_line(tmp_path):
    src, example = _scan_project(tmp_path)
    result = runner.invoke(app, ["scan", str(src), "-a", str(example), "-f", "github"])
    assert ",line=3," in result.output
    assert "NEW_SECRET is read here" in result.output
