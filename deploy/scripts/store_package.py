#!/usr/bin/env python3
"""Build and validate the root-level ZIP uploaded to Chrome Web Store.

This package is deliberately separate from the nested Moodle pilot archive.  It
contains only generated extension output, has stable ZIP metadata, and writes a
small JSON report alongside the ZIP for release verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path


UPDATE_HOST = "https://radicalmove.github.io/Beta-testing-app/*"
STORE_FILES = (
    "background.js",
    "content.js",
    "icons/icon128.png",
    "icons/icon16.png",
    "icons/icon48.png",
    "manifest.json",
)

_SEMVER = re.compile(r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")
_PRIVATE_KEY = re.compile(r"(?:^|[-_.])(private|secret)(?:[-_.]|$)|\.(?:pem|key)$", re.I)
_REMOTE_EXECUTABLE = re.compile(
    r"(?:\bimportScripts\s*\(|<script[^>]+\bsrc\s*=\s*[\"']https?://|"
    r"(?:src|href)\s*=\s*[\"']https?://[^\"']+\.(?:js|mjs)(?:[?#\"']))",
    re.I,
)


def report_path_for(output: Path) -> Path:
    """Return the deterministic JSON report path corresponding to *output*."""

    return output.with_suffix(".report.json")


def _all_files(dist: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(dist.rglob("*")):
        relative = path.relative_to(dist).as_posix()
        if path.is_symlink():
            raise ValueError(f"symlink is not allowed in Web Store package: {relative}")
        if path.is_dir():
            continue
        files.append(relative)
    return files


def _validate_manifest(dist: Path, version: str, files: set[str]) -> dict:
    manifest_path = dist / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("manifest.json is required")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("manifest.json is not valid JSON") from error
    if not isinstance(manifest, dict) or manifest.get("manifest_version") != 3:
        raise ValueError("manifest must be Manifest V3")
    if manifest.get("version") != version:
        raise ValueError(f"manifest version does not match requested version {version}")
    if not isinstance(manifest.get("name"), str) or not manifest["name"].startswith("RADCRA"):
        raise ValueError("manifest name must identify RADCRA")
    if "THIS EXTENSION IS FOR BETA TESTING" not in str(manifest.get("description", "")):
        raise ValueError("manifest description must contain the beta-testing disclosure")
    icons = manifest.get("icons")
    expected_icons = {"16": "icons/icon16.png", "48": "icons/icon48.png", "128": "icons/icon128.png"}
    if icons != expected_icons or any(path not in files for path in expected_icons.values()):
        raise ValueError("manifest must reference all required generated icons")
    permissions = manifest.get("host_permissions", [])
    if not isinstance(permissions, list) or UPDATE_HOST not in permissions:
        raise ValueError("manifest must include the fixed GitHub Pages update host")
    for permission in permissions:
        if not isinstance(permission, str) or ".invalid" in permission or "example.invalid" in permission:
            raise ValueError("manifest contains a placeholder host permission")
    return manifest


def validate_store_directory(dist: Path, version: str) -> list[str]:
    """Validate generated production output and return package file names.

    The validator is intentionally strict about files that could leak release
    metadata or private signing material, while allowing any generated runtime
    chunks/assets that a future build may add.
    """

    dist = Path(dist)
    if not dist.is_dir():
        raise ValueError(f"distribution directory does not exist: {dist}")
    if not _SEMVER.fullmatch(version) or version == "0.0.0":
        raise ValueError(f"invalid release version: {version}")
    files = _all_files(dist)
    if not files:
        raise ValueError("distribution directory is empty")
    for name in files:
        path = Path(name)
        lower = name.lower()
        if path.suffix == ".map":
            raise ValueError(f"source map is not allowed in Web Store package: {name}")
        if name in {"RELEASE.json", "SHA256SUMS"} or lower.endswith(".report.json"):
            raise ValueError(f"release metadata is not allowed in Web Store package: {name}")
        if _PRIVATE_KEY.search(name):
            raise ValueError(f"private key is not allowed in Web Store package: {name}")
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe package path: {name}")
    _validate_manifest(dist, version, set(files))
    for name in files:
        if Path(name).suffix.lower() not in {".js", ".mjs", ".html", ".css"}:
            continue
        source = (dist / name).read_text(encoding="utf-8", errors="strict")
        if _REMOTE_EXECUTABLE.search(source):
            raise ValueError(f"remote executable reference is not allowed: {name}")
    return files


def _write_deterministic_zip(dist: Path, output: Path, files: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, (dist / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def package_store(dist: Path, output: Path, version: str, repository: str) -> dict:
    """Validate *dist*, create deterministic *output*, and return its report."""

    if not repository or repository.strip() != repository or "/" not in repository:
        raise ValueError("repository must be an owner/name value")
    files = validate_store_directory(Path(dist), version)
    files = sorted(files)
    _write_deterministic_zip(Path(dist), Path(output), files)
    zip_bytes = Path(output).read_bytes()
    report = {
        "schema_version": 1,
        "version": version,
        "repository": repository,
        "files": files,
        "zip_sha256": hashlib.sha256(zip_bytes).hexdigest(),
    }
    report_path_for(Path(output)).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    report = package_store(args.dist, args.output, args.version, args.repository)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
