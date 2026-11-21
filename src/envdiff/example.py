"""Generate a safe .env.example template from a real .env file."""

from __future__ import annotations

from envdiff.parser import BOM, parse_line
from envdiff.redact import is_secret_key, mask_url_password


def _format_value(value: str) -> str:
    """Quote a value if writing it bare would change how it parses."""
    if value == "" or any(ch in value for ch in (" ", "#", "'", '"', "\t")):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"' if value else ""
    return value


def make_example(text: str, keep_values: bool = False) -> str:
    """Return a .env.example version of `text`.

    Comments and blank lines are kept so the template stays readable.
    Values are removed. With `keep_values`, values of non-secret keys are kept,
    except values that contain a password inside a URL.
    Unparsable lines and repeated keys are dropped.
    """
    out: list[str] = []
    seen: set[str] = set()
    for raw_line in text.lstrip(BOM).splitlines():
        parsed = parse_line(raw_line)
        if parsed.kind in ("blank", "comment"):
            out.append(raw_line.rstrip())
            continue
        if parsed.kind != "assign" or parsed.key in seen:
            continue
        seen.add(parsed.key)
        value = parsed.value
        safe = (
            keep_values
            and not is_secret_key(parsed.key)
            and mask_url_password(value) == value
        )
        out.append(f"{parsed.key}={_format_value(value) if safe else ''}")
    return "\n".join(out) + "\n"
