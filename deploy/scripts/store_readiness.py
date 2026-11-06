#!/usr/bin/env python3
"""Validate the explicit Sphere Chrome Web Store submission workspace."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image
if __package__:
    from .store_package import STORE_FILES
else:
    from store_package import STORE_FILES


REPOSITORY = "radicalmove/radcra"
PUBLIC_ORIGIN = "https://radicalmove.github.io/sphere/"
CONTACT = "rcadavies@gmail.com"
NAME = "Sphere - Course Review App (BETA)"
CHECK_NAMES = ("identity", "public_site", "privacy_disclosure", "support", "promo", "screenshot", "package", "checksum", "production_inputs")
REPORT_FIELDS = {
    "schema_version", "version", "repository", "build_mode", "build_commit",
    "moodle_patterns", "optional_frame_patterns", "review_service_origin",
    "manifest_sha256", "public_key_sha256", "files", "zip_sha256",
}
FORBIDDEN_TEXT = ("radicalmove/Beta-testing-app", "radicalmove.github.io/Beta-testing-app", "richard.davies@canterbury.ac.nz")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def valid_https(value: str) -> bool:
    return bool(re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/\*)?", value)) and not re.search(r"(?:\.invalid|\.test|\.example)(?:[:/]|$)|placeholder|localhost|127\.0\.0\.1", value, re.I)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("fixture", "submission"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--package-report", required=True, type=Path)
    parser.add_argument("--checksum", required=True, type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    promo = root / "store-assets/sphere-promo-440x280.png"
    default_screenshot = root / "store-assets/sphere-screenshot-1280x800.png"
    screenshot = args.screenshot.resolve() if args.screenshot else default_screenshot
    checks = {name: False for name in CHECK_NAMES}
    errors: list[str] = []

    public_paths = (
        root / "README.md", root / "docs/privacy-policy.md",
        root / "docs/chrome-web-store-listing.md", root / "docs/chrome-web-store-reviewer-guide.md",
        root / "site/index.html", root / "site/privacy/index.html", root / "site/support/index.html",
    )
    try:
        texts = [read_text(path) for path in public_paths]
        joined = "\n".join(texts)
        if any(old in joined for old in FORBIDDEN_TEXT):
            raise ValueError
        if NAME not in texts[2] or CONTACT not in joined or PUBLIC_ORIGIN not in joined:
            raise ValueError
        checks["identity"] = True
    except (OSError, ValueError):
        errors.append("identity_invalid")

    try:
        latest = json.loads(read_text(root / "site/latest.json"))
        if latest.get("schema_version") != 1 or latest.get("release_url") != "https://github.com/radicalmove/radcra/releases/tag/v" + latest.get("version", ""):
            raise ValueError
        download = latest.get("download_url", "")
        if download != PUBLIC_ORIGIN or download.lower().endswith((".zip", ".crx")):
            raise ValueError
        for path in (root / "site/index.html", root / "site/privacy/index.html", root / "site/support/index.html"):
            if not path.is_file():
                raise ValueError
        checks["public_site"] = True
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        errors.append("public_site_invalid")

    try:
        privacy = read_text(root / "docs/privacy-policy.md") + read_text(root / "site/privacy/index.html")
        required = ("reviewer name", "email", "credentials", "course/page URLs", "selected text", "comments", "screenshots", "operational", "HTTPS", "retention", "delet", "Limited Use")
        if not all(value.lower() in privacy.lower() for value in required):
            raise ValueError
        checks["privacy_disclosure"] = True
    except (OSError, ValueError):
        errors.append("privacy_disclosure_invalid")

    try:
        support = read_text(root / "site/support/index.html")
        reviewer = read_text(root / "docs/chrome-web-store-reviewer-guide.md")
        if CONTACT not in support or "out-of-band" not in reviewer or "credential" not in reviewer.lower():
            raise ValueError
        checks["support"] = True
    except (OSError, ValueError):
        errors.append("support_evidence_missing")

    try:
        with Image.open(promo) as image:
            if image.format != "PNG" or image.size != (440, 280) or image.info:
                raise ValueError
        notes = read_text(root / "store-assets/README.md").lower()
        if not re.search(r"saniti[sz]", notes) or "upload only" not in notes:
            raise ValueError
        checks["promo"] = True
    except (OSError, ValueError):
        errors.append("promo_invalid")

    if screenshot.is_file():
        try:
            with Image.open(screenshot) as image:
                if image.format != "PNG" or image.size != (1280, 800) or image.info:
                    raise ValueError
            checks["screenshot"] = True
        except (OSError, ValueError):
            errors.append("screenshot_invalid")
    else:
        errors.append("screenshot_missing")

    report = None
    manifest = None
    fixture_public_key_path = root / "tests/fixtures/store-public-key.txt"
    fixture_public_key = None
    try:
        fixture_public_key = read_text(fixture_public_key_path).strip()
        base64.b64decode(fixture_public_key, validate=True)
    except (OSError, ValueError):
        errors.append("fixture_public_key_missing")
    archive_path = args.package_report.with_name(args.package_report.name.removesuffix(".report.json") + ".zip")
    try:
        report = json.loads(read_text(args.package_report))
        if set(report) != REPORT_FIELDS or report["repository"] != REPOSITORY or report["schema_version"] != 1:
            raise ValueError
        archive_bytes = archive_path.read_bytes()
        if digest(archive_bytes) != report["zip_sha256"]:
            raise ValueError
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            if names != list(STORE_FILES) or report["files"] != list(STORE_FILES) or any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in names):
                raise ValueError
            if any(name.lower().endswith((".map", ".pem", ".key", ".zip", ".crx")) or "promo" in name.lower() or "screenshot" in name.lower() or re.search(r"(?:^|[-_.])key(?:[-_.]|$)", PurePosixPath(name).name, re.I) for name in names):
                raise ValueError
            manifest_bytes = archive.read("manifest.json")
            manifest = json.loads(manifest_bytes)
            if digest(manifest_bytes) != report["manifest_sha256"] or manifest.get("version") != report["version"]:
                raise ValueError
            moodle_patterns = manifest.get("content_scripts", [{}])[0].get("matches")
            optional_patterns = manifest.get("optional_host_permissions", [])
            host_permissions = manifest.get("host_permissions", [])
            service_patterns = [item for item in host_permissions if item not in (moodle_patterns or []) and item != "https://radicalmove.github.io/sphere/*"]
            if (moodle_patterns != report["moodle_patterns"] or optional_patterns != report["optional_frame_patterns"] or len(service_patterns) != 1
                    or not service_patterns[0].endswith("/*") or service_patterns[0][:-2] != report["review_service_origin"]):
                raise ValueError
            build_commit = report["build_commit"]
            if report["build_mode"] != "production" or not re.fullmatch(r"[0-9a-f]{40}", build_commit):
                raise ValueError
            for runtime in ("background.js", "content.js"):
                if build_commit.encode("ascii") not in archive.read(runtime):
                    raise ValueError
            if report["review_service_origin"].encode("utf-8") not in archive.read("background.js"):
                raise ValueError
            key_der = base64.b64decode(manifest["key"], validate=True)
            if digest(key_der) != report["public_key_sha256"]:
                raise ValueError
            for size in (16, 48, 128):
                with Image.open(io.BytesIO(archive.read(f"icons/icon{size}.png"))) as icon:
                    if icon.size != (size, size):
                        raise ValueError
                    if size == 128:
                        if icon.mode != "RGBA" or icon.getchannel("A").getbbox() != (16, 16, 112, 112):
                            raise ValueError
        package_version = json.loads(read_text(root / "extension/package.json"))["version"]
        if package_version != report["version"]:
            raise ValueError
        checks["package"] = True
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile):
        errors.append("package_invalid")

    try:
        checksum_parts = read_text(args.checksum).strip().split()
        if len(checksum_parts) != 2 or checksum_parts[0] != digest(archive_path.read_bytes()) or checksum_parts[1].lstrip("*") != archive_path.name:
            raise ValueError
        checks["checksum"] = True
    except (OSError, ValueError):
        errors.append("checksum_invalid")

    if checks["package"] and report is not None and manifest is not None:
        production_errors = []
        try:
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
            if report["build_mode"] != "production" or report["build_commit"] != head:
                production_errors.append("production_build_commit_mismatch")
            patterns = [*report["moodle_patterns"], *report["optional_frame_patterns"]]
            if not patterns or not all(valid_https(pattern) for pattern in patterns) or not valid_https(report["review_service_origin"]):
                production_errors.append("production_origin_invalid")
            if manifest.get("content_scripts", [{}])[0].get("matches") != report["moodle_patterns"] or manifest.get("optional_host_permissions", []) != report["optional_frame_patterns"]:
                production_errors.append("production_manifest_evidence_mismatch")
            key_digest = report["public_key_sha256"]
            if fixture_public_key is None:
                raise ValueError
            dev_manifest = json.loads(read_text(root / "extension/public/manifest.json"))
            forbidden_key_digests = {digest(base64.b64decode(fixture_public_key, validate=True)), digest(base64.b64decode(dev_manifest["key"], validate=True))}
            if key_digest in forbidden_key_digests:
                production_errors.append("production_public_key_not_unique")
        except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError):
            production_errors.append("production_inputs_invalid")
        if not production_errors:
            checks["production_inputs"] = True
        if args.mode == "submission":
            errors.extend(production_errors)

    manual_screenshot_required = not checks["screenshot"]
    if args.mode == "fixture":
        ready = all(checks[name] for name in CHECK_NAMES if name not in ("screenshot", "production_inputs")) and all(error == "screenshot_missing" or error.startswith("production_") for error in errors)
    else:
        ready = all(checks.values()) and not errors
    output = {"schema_version": 1, "mode": args.mode, "ready": ready, "manual_screenshot_required": manual_screenshot_required, "checks": checks, "errors": sorted(set(errors))}
    print(json.dumps(output, separators=(",", ":")))
    raise SystemExit(0 if ready else 1)


if __name__ == "__main__":
    main()
