# src/magic_optimizer/exporters/name_list.py
from __future__ import annotations

from collections import Counter
from pathlib import Path


def _collapsed_lines(names: list[str]) -> list[str]:
    counts = Counter(str(n) for n in names)
    return [f"{qty} {name}" for name, qty in sorted(counts.items(), key=lambda x: x[0])]


def to_copy_paste(names: list[str]) -> str:
    return "\n".join(_collapsed_lines(names)) + ("\n" if names else "")


def to_arena_text(names: list[str], *, title: str = "") -> str:
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
        lines.append("")
    lines.extend(_collapsed_lines(names))
    return "\n".join(lines) + ("\n" if lines else "")


def write_arena_file(
    path: str | Path,
    names: list[str],
    *,
    title: str = "",
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(to_arena_text(names, title=title), encoding="utf-8")
    return target
