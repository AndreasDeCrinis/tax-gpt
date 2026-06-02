from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import taxgpt


SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


def test_version_is_semver_and_in_sync():
    version = Path("VERSION").read_text(encoding="utf-8").strip()

    assert SEMVER.match(version)
    assert taxgpt.__version__ == version


def test_semantic_release_version_script_updates_all_version_files(tmp_path):
    script = Path("scripts/update_version.py").resolve()
    project_files = {
        "VERSION": Path("VERSION").read_text(encoding="utf-8"),
        "pyproject.toml": Path("pyproject.toml").read_text(encoding="utf-8"),
        "taxgpt/__init__.py": Path("taxgpt/__init__.py").read_text(encoding="utf-8"),
    }

    for relative_path, content in project_files.items():
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    subprocess.run([sys.executable, str(script), "1.2.3"], cwd=tmp_path, check=True)

    assert (tmp_path / "VERSION").read_text(encoding="utf-8") == "1.2.3\n"
    assert 'version = "1.2.3"' in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert '__version__ = "1.2.3"' in (tmp_path / "taxgpt/__init__.py").read_text(encoding="utf-8")
