"""Compare two parsed .env mappings."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiffResult:
    """Differences of `other` relative to `base`.

    missing: keys present in base but absent from other.
    extra:   keys present in other but absent from base.
    empty:   keys present in other whose value is empty (may be intentional).
    """

    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.missing or self.extra)

    @property
    def has_issues(self) -> bool:
        return self.has_errors or bool(self.empty)


def compare(base: dict[str, str], other: dict[str, str]) -> DiffResult:
    """Compare `other` against `base`. Key order follows `base`, then `other`."""
    missing = [k for k in base if k not in other]
    extra = [k for k in other if k not in base]
    empty = [k for k in other if other[k] == "" and k in base]
    return DiffResult(missing=missing, extra=extra, empty=empty)
