from __future__ import annotations

import re
import sys
from pathlib import Path


VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


def main() -> int:
    if len(sys.argv) != 2 or not VERSION_PATTERN.fullmatch(sys.argv[1]):
        print("Usage: update_version.py <semver>", file=sys.stderr)
        return 2

    version = sys.argv[1]
    write_version_file(version)
    replace_once(Path("pyproject.toml"), r'(?m)^version = "[^"]+"$', f'version = "{version}"')
    replace_once(Path("taxgpt/__init__.py"), r'__version__ = "[^"]+"', f'__version__ = "{version}"')
    return 0


def write_version_file(version: str) -> None:
    Path("VERSION").write_text(f"{version}\n", encoding="utf-8")


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    original = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, original, count=1)
    if count != 1:
        raise RuntimeError(f"Expected exactly one replacement in {path}, got {count}")
    path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
