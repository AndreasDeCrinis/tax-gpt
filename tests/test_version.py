from __future__ import annotations

import re
from pathlib import Path

import taxgpt


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


def test_version_is_semver_and_in_sync():
    version = Path("VERSION").read_text(encoding="utf-8").strip()

    assert SEMVER.match(version)
    assert taxgpt.__version__ == version
