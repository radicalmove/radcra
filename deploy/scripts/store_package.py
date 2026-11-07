#!/usr/bin/env python3
"""Build and validate the root-level ZIP uploaded to Chrome Web Store.

This package is deliberately separate from the nested Moodle pilot archive.  It
contains only generated extension output, has stable ZIP metadata, and writes a
small JSON report alongside the ZIP for release verification.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path


UPDATE_HOST = "https://radicalmove.github.io/sphere/*"
REPOSITORY = "radicalmove/radcra"
STORE_NAME = "Sphere - Course Review App (BETA)"
STORE_FILES = (
    "background.js",
    "content.js",
    "fonts/OFL.txt",
    "fonts/Poppins-Bold.ttf",
    "fonts/Poppins-Medium.ttf",
    "fonts/Poppins-Regular.ttf",
    "fonts/Poppins-SemiBold.ttf",
    "icons/icon128.png",
    "icons/icon16.png",
    "icons/icon48.png",
    "manifest.json",
    "sphere-controls.html",
    "sphere-controls.js",
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
    if manifest.get("name") != STORE_NAME:
        raise ValueError(f"manifest name must be {STORE_NAME}")
    if manifest.get("action", {}).get("default_popup") != "sphere-controls.html":
        raise ValueError("manifest must reference the bundled Sphere controls")
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
        if not isinstance(permission, str) or re.search(r"(?:\.invalid|\.test|\.example)(?:[:/]|$)|localhost|127\.0\.0\.1", permission, re.I):
            raise ValueError("manifest contains a placeholder host permission")
    try:
        key = base64.b64decode(manifest["key"], validate=True)
        if base64.b64encode(key).decode("ascii") != manifest["key"] or len(key) < 256 or not key.startswith(b"\x30"):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError("manifest public key must be canonical RSA SPKI DER base64") from None
    return manifest


def validate_store_directory(dist: Path, version: str) -> list[str]:
    """Validate generated production output and return package file names.

    The validator is intentionally strict about files that could leak release
    metadata or private signing material, and admits only the declared runtime files.
    """

    dist = Path(dist)
    if not dist.is_dir():
        raise ValueError(f"distribution directory does not exist: {dist}")
    if not _SEMVER.fullmatch(version) or version == "0.0.0":
        raise ValueError(f"invalid release version: {version}")
    files = _all_files(dist)
    if not files:
        raise ValueError("distribution directory is empty")
    unexpected = sorted(set(files) - set(STORE_FILES))
    missing = sorted(set(STORE_FILES) - set(files))
    if unexpected or missing:
        details = []
        if unexpected:
            details.append(f"not an allowed runtime file: {', '.join(unexpected)}")
        if missing:
            details.append(f"required runtime file missing: {', '.join(missing)}")
        raise ValueError("; ".join(details))
    for name in files:
        path = Path(name)
        lower = name.lower()
        if path.suffix == ".map":
            raise ValueError(f"source map is not allowed in Web Store package: {name}")
        if path.suffix.lower() in {".zip", ".crx"}:
            raise ValueError(f"nested archive is not allowed in Web Store package: {name}")
        if name in {"RELEASE.json", "SHA256SUMS"} or lower.endswith(".report.json"):
            raise ValueError(f"release metadata is not allowed in Web Store package: {name}")
        if _PRIVATE_KEY.search(name):
            raise ValueError(f"private key is not allowed in Web Store package: {name}")
        if re.search(r"(?:^|[-_.])key(?:[-_.]|$)", path.name, re.I):
            raise ValueError(f"key file is not allowed in Web Store package: {name}")
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


def package_store(dist: Path, output: Path, version: str, repository: str, build_commit: str) -> dict:
    """Validate *dist*, create deterministic *output*, and return its report."""

    if repository != REPOSITORY:
        raise ValueError(f"repository must be {REPOSITORY}")
    if not re.fullmatch(r"[0-9a-f]{40}", build_commit):
        raise ValueError("build commit must be a full lowercase commit")
    files = validate_store_directory(Path(dist), version)
    for runtime in ("background.js", "content.js"):
        if build_commit not in (Path(dist) / runtime).read_text(encoding="utf-8"):
            raise ValueError(f"full build commit is missing from runtime diagnostics: {runtime}")
    files = sorted(files)
    _write_deterministic_zip(Path(dist), Path(output), files)
    zip_bytes = Path(output).read_bytes()
    manifest_bytes = (Path(dist) / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    host_permissions = manifest["host_permissions"]
    moodle_patterns = [pattern for script in manifest["content_scripts"] for pattern in script["matches"]]
    service_patterns = [item for item in host_permissions if item not in moodle_patterns and item != UPDATE_HOST]
    demo_pattern = "https://fld-mini.tail4ccaba.ts.net:8443/*"
    has_reviewer_demo = demo_pattern in service_patterns and any(pattern.startswith("https://fld-mini.tail4ccaba.ts.net/course/") for pattern in moodle_patterns)
    if has_reviewer_demo:
        service_patterns.remove(demo_pattern)
    if len(service_patterns) != 1:
        raise ValueError("manifest must contain exactly one review service origin")
    review_service_origin = service_patterns[0][:-2]
    if review_service_origin not in (Path(dist) / "background.js").read_text(encoding="utf-8"):
        raise ValueError("review service origin is missing from background runtime evidence")
    public_key = base64.b64decode(manifest["key"], validate=True)
    report = {
        "schema_version": 1,
        "version": version,
        "repository": repository,
        "build_mode": "production",
        "build_commit": build_commit,
        "moodle_patterns": moodle_patterns,
        "optional_frame_patterns": manifest.get("optional_host_permissions", []),
        "review_service_origin": review_service_origin,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "public_key_sha256": hashlib.sha256(public_key).hexdigest(),
        "files": files,
        "zip_sha256": hashlib.sha256(zip_bytes).hexdigest(),
    }
    if has_reviewer_demo:
        report["reviewer_demo_origin"] = demo_pattern[:-2]
    report_path_for(Path(output)).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--build-commit", required=True)
    args = parser.parse_args()
    report = package_store(args.dist, args.output, args.version, args.repository, args.build_commit)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
