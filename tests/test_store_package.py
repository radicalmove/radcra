import hashlib
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from deploy.scripts.store_package import (
    STORE_FILES,
    package_store,
    report_path_for,
    validate_store_directory,
)


class StorePackageTests(unittest.TestCase):
    BUILD_COMMIT = "0123456789abcdef0123456789abcdef01234567"
    def fixture(self, root: Path, *, version: str = "0.5.35") -> Path:
        dist = root / "dist"
        (dist / "icons").mkdir(parents=True)
        (dist / "background.js").write_text(f"self.background = true;/*{self.BUILD_COMMIT}|https://fld-mini.tail4ccaba.ts.net*/\n")
        (dist / "content.js").write_text(f"(() => {{ document.documentElement.dataset.active = 'yes'; }})();/*{self.BUILD_COMMIT}*/\n")
        manifest = {
            "manifest_version": 3,
            "name": "Sphere - Course Review App (BETA)",
            "version": version,
            "description": "Review Moodle pages. THIS EXTENSION IS FOR BETA TESTING.",
            "icons": {"16": "icons/icon16.png", "48": "icons/icon48.png", "128": "icons/icon128.png"},
            "key": (Path(__file__).parent / "fixtures/store-public-key.txt").read_text().strip(),
            "permissions": ["storage"],
            "host_permissions": [
                "https://my.uconline.ac.nz/*",
                "https://fld-mini.tail4ccaba.ts.net/*",
                "https://radicalmove.github.io/sphere/*",
            ],
            "optional_host_permissions": ["https://packages.articulateusercontent.com/*"],
            "background": {"service_worker": "background.js"},
            "action": {"default_popup": "sphere-controls.html"},
            "content_scripts": [{"matches": ["https://my.uconline.ac.nz/*"], "js": ["content.js"]}],
        }
        (dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        for size in (16, 48, 128):
            (dist / "icons" / f"icon{size}.png").write_bytes(b"PNG" + bytes([size]))
        for name in STORE_FILES:
            path = dist / name
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
        return dist

    def test_package_is_root_level_deterministic_and_reports_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = self.fixture(root)
            output = root / "sphere-web-store-v0.5.35.zip"
            first = package_store(dist, output, "0.5.35", "radicalmove/radcra", self.BUILD_COMMIT)
            first_bytes = output.read_bytes()
            second = package_store(dist, output, "0.5.35", "radicalmove/radcra", self.BUILD_COMMIT)
            self.assertEqual(first, second)
            self.assertEqual(first_bytes, output.read_bytes())
            self.assertEqual(report_path_for(output), output.with_suffix(".report.json"))
            self.assertEqual(first["files"], list(STORE_FILES))
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), list(STORE_FILES))
                self.assertTrue(all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist()))
                self.assertTrue(all(not name.startswith("moodle-review-extension/") for name in archive.namelist()))
            report = json.loads(report_path_for(output).read_text())
            self.assertEqual(report["version"], "0.5.35")
            self.assertEqual(report["repository"], "radicalmove/radcra")
            self.assertEqual(report["zip_sha256"], hashlib.sha256(first_bytes).hexdigest())
            self.assertEqual(report["build_mode"], "production")
            self.assertEqual(report["build_commit"], self.BUILD_COMMIT)
            self.assertEqual(report["moodle_patterns"], ["https://my.uconline.ac.nz/*"])
            self.assertEqual(report["optional_frame_patterns"], ["https://packages.articulateusercontent.com/*"])
            self.assertEqual(report["review_service_origin"], "https://fld-mini.tail4ccaba.ts.net")
            self.assertEqual(report["manifest_sha256"], hashlib.sha256((dist / "manifest.json").read_bytes()).hexdigest())
            self.assertEqual(report["public_key_sha256"], hashlib.sha256(__import__("base64").b64decode(json.loads((dist / "manifest.json").read_text())["key"])).hexdigest())

    def test_validator_rejects_release_metadata_private_keys_maps_and_remote_code(self):
        bad_files = (
            "RELEASE.json",
            "source.js.map",
            "SOURCE.MAP",
            "pilot-private.pem",
            "listing-art.png",
            "sphere-promo-440x280.png",
            "README.txt",
        )
        for bad_file in bad_files:
            with self.subTest(bad_file=bad_file), tempfile.TemporaryDirectory() as directory:
                dist = self.fixture(Path(directory))
                path = dist / bad_file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("not package content")
                with self.assertRaisesRegex(ValueError, "(not an allowed runtime file|release metadata|source map|private key)"):
                    validate_store_directory(dist, "0.5.35")
        with tempfile.TemporaryDirectory() as directory:
            dist = self.fixture(Path(directory))
            (dist / "content.js").write_text("importScripts('https://evil.example.test/remote.js');")
            with self.assertRaisesRegex(ValueError, "remote executable"):
                validate_store_directory(dist, "0.5.35")

    def test_validator_rejects_placeholder_host_and_identity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            dist = self.fixture(Path(directory))
            manifest_path = dist / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["host_permissions"][1] = "https://review.example.invalid/*"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "placeholder"):
                validate_store_directory(dist, "0.5.35")
        with tempfile.TemporaryDirectory() as directory:
            dist = self.fixture(Path(directory), version="0.5.34")
            with self.assertRaisesRegex(ValueError, "version"):
                validate_store_directory(dist, "0.5.35")

    def test_cli_defaults_to_radicalmove_radcra_and_writes_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = self.fixture(root)
            output = root / "store.zip"
            result = subprocess.run(
                [
                    "python3",
                    "deploy/scripts/store_package.py",
                    "--dist",
                    str(dist),
                    "--output",
                    str(output),
                    "--version",
                    "0.5.35",
                    "--build-commit",
                    self.BUILD_COMMIT,
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertTrue(report_path_for(output).is_file())

    def test_package_rejects_wrong_repository_or_missing_runtime_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "repository"):
                package_store(dist, root / "bad.zip", "0.5.35", "radicalmove/Beta-testing-app", self.BUILD_COMMIT)
            (dist / "content.js").write_text("no diagnostic")
            with self.assertRaisesRegex(ValueError, "build commit"):
                package_store(dist, root / "bad.zip", "0.5.35", "radicalmove/radcra", self.BUILD_COMMIT)


if __name__ == "__main__":
    unittest.main()
