from pathlib import Path

from envdiff.scan import find_usages_in_text, scan


def names(text: str) -> list[str]:
    return [u.name for u in find_usages_in_text(text, Path("x"))]


def test_python_patterns():
    text = (
        'a = os.getenv("A")\n'
        "b = os.environ.get('B', 'x')\n"
        'c = os.environ["C"]\n'
        'd = environ.get("D")\n'
        'e = getenv("E")\n'
    )
    assert names(text) == ["A", "B", "C", "D", "E"]


def test_javascript_patterns():
    text = (
        "const a = process.env.API_URL;\n"
        "const b = process.env['TOKEN'];\n"
        "const c = import.meta.env.VITE_TITLE;\n"
    )
    assert names(text) == ["API_URL", "TOKEN", "VITE_TITLE"]


def test_go_ruby_rust_patterns():
    text = (
        'port := os.Getenv("PORT")\n'
        'key = ENV.fetch("SECRET_KEY")\n'
        'host = ENV["HOST"]\n'
        'let url = std::env::var("DATABASE_URL")\n'
    )
    assert names(text) == ["PORT", "SECRET_KEY", "HOST", "DATABASE_URL"]


def test_line_numbers_are_reported():
    usages = find_usages_in_text('x = 1\ny = os.getenv("Y")\n', Path("f.py"))
    assert usages[0].line == 2


def test_dynamic_names_are_not_matched():
    assert names("os.getenv(name)\nprocess.env[key]\n") == []


def test_scan_skips_dependency_folders(tmp_path):
    (tmp_path / "app.py").write_text('os.getenv("USED")\n', encoding="utf-8")
    deps = tmp_path / "node_modules" / "lib"
    deps.mkdir(parents=True)
    (deps / "index.js").write_text("process.env.FROM_DEPS\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text('os.getenv("NOT_CODE")\n', encoding="utf-8")
    assert list(scan([tmp_path])) == ["USED"]
