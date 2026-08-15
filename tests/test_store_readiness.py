import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import yaml
from PIL import Image
from deploy.scripts.store_package import package_store, report_path_for


ROOT = Path(__file__).resolve().parents[1]
PROMO_SHA256 = "b8fbe0cc77266d965e9592265df9c813fe112af47fde4697819172bafffce957"
FONT_SHA256 = "e6476c1b80502924294eed40894c5b18e06c181444ca953e5334262df9c27724"
ICON_SHA256 = {
    16: "503eb3ec45ca847e91a32f338c7bd6103ace8f6105c3cb503b2b7c84e76d87e6",
    48: "d9214abb18ad56fd804d053da3220a93b79df4dd4d708af062d52d643400011c",
    128: "591c6dca5d18dd926dad48ba6bc9189359beacff7c2db1c73072e695ffe6b39c",
}


class StoreReadinessTests(unittest.TestCase):
    def run_generator(self, script: str, *arguments: str) -> None:
        subprocess.run(["python3", f"scripts/{script}", *arguments], cwd=ROOT, check=True)

    def test_extension_icons_are_deterministic_rgba_and_use_safe_area(self):
        paths = [ROOT / "extension" / "public" / "icons" / f"icon{size}.png" for size in (16, 48, 128)]
        committed = [path.read_bytes() for path in paths]
        for size, contents in zip((16, 48, 128), committed):
            self.assertEqual(hashlib.sha256(contents).hexdigest(), ICON_SHA256[size])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "icons"
            self.run_generator("generate-extension-icons.py", "--output-directory", str(output))
            first = [(output / path.name).read_bytes() for path in paths]
            self.assertEqual(first, committed)
            self.run_generator("generate-extension-icons.py", "--output-directory", str(output))
            self.assertEqual(first, [(output / path.name).read_bytes() for path in paths])
        for path, size in zip(paths, (16, 48, 128)):
            with Image.open(path) as image:
                self.assertEqual(image.size, (size, size))
                self.assertEqual(image.mode, "RGBA")
        with Image.open(paths[-1]) as image:
            left, top, right, bottom = image.getchannel("A").getbbox()
            self.assertGreaterEqual(left, 16)
            self.assertGreaterEqual(top, 16)
            self.assertLessEqual(right, 112)
            self.assertLessEqual(bottom, 112)

    def test_promo_is_deterministic_approved_png_with_documented_provenance(self):
        promo = ROOT / "store-assets" / "radcra-promo-440x280.png"
        self.assertEqual(hashlib.sha256(promo.read_bytes()).hexdigest(), PROMO_SHA256)
        committed = promo.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / promo.name
            self.run_generator("generate-store-assets.py", "--output", str(output))
            first = output.read_bytes()
            self.assertEqual(first, committed)
            self.run_generator("generate-store-assets.py", "--output", str(output))
            self.assertEqual(first, output.read_bytes())
        with Image.open(promo) as image:
            self.assertEqual(image.size, (440, 280))
            self.assertIn(image.mode, ("RGB", "RGBA"))

        generator = (ROOT / "scripts" / "generate-store-assets.py").read_text()
        bundled_font = ROOT / "store-assets" / "source" / "DejaVuSans-Bold.ttf"
        self.assertTrue(bundled_font.is_file())
        self.assertEqual(hashlib.sha256(bundled_font.read_bytes()).hexdigest(), FONT_SHA256)
        self.assertIn('FONT = ROOT / "store-assets" / "source" / "DejaVuSans-Bold.ttf"', generator)
        self.assertNotIn("FONT_CANDIDATES", generator)
        self.assertNotIn("/System/Library/Fonts", generator)
        self.assertNotIn("/usr/share/fonts", generator)
        self.assertIn('"RADCRA"', generator)
        self.assertIn('"Course Review App"', generator)
        for forbidden in ("University of Canterbury", "Google", "Chrome Web Store"):
            self.assertNotIn(forbidden, generator)

        source_notes = (ROOT / "store-assets" / "source" / "README.md").read_text()
        upload_notes = (ROOT / "store-assets" / "README.md").read_text()
        self.assertRegex(source_notes.lower(), r"provenance|generated")
        self.assertRegex(source_notes.lower(), r"font")
        self.assertRegex(source_notes, r"DejaVu Fonts 2\.37")
        self.assertTrue((ROOT / "store-assets" / "source" / "DEJAVU-LICENSE.txt").is_file())
        self.assertRegex(upload_notes.lower(), r"upload")
        self.assertRegex(upload_notes.lower(), r"saniti[sz]")

    def test_release_workflow_runs_store_readiness_suite(self):
        workflow = (ROOT / ".github" / "workflows" / "release-extension.yml").read_text()
        self.assertIn("tests/test_store_readiness.py", workflow)
        self.assertIn("tests/test_release_artifacts.py", workflow)

    def test_tagged_release_builds_and_gates_exact_store_evidence_before_publish(self):
        workflow = (ROOT / ".github" / "workflows" / "release-extension.yml").read_text()
        self.assertIsInstance(yaml.safe_load(workflow), dict)
        unit_tests = workflow.index("Run deployment, store, and public-site tests")
        build = workflow.index("Build production extension with ephemeral key")
        package = workflow.index("Package pilot and Web Store artifacts in isolated runner storage")
        gate = workflow.index("Verify exact Web Store submission evidence")
        publish = workflow.index("Publish GitHub release assets and notes")
        self.assertLess(unit_tests, build)
        self.assertLess(build, package)
        self.assertLess(package, gate)
        self.assertLess(gate, publish)
        artifacts = '$RUNNER_TEMP/radcra-release-assets'
        exact_gate = '''python3 deploy/scripts/store_readiness.py --mode submission --root "$GITHUB_WORKSPACE" --package-report "$artifacts/radcra-web-store-v${release_version}.report.json" --checksum "$artifacts/radcra-web-store-v${release_version}.zip.sha256" --screenshot "$GITHUB_WORKSPACE/store-assets/radcra-screenshot-1280x800.png"'''
        self.assertIn(artifacts, workflow)
        self.assertIn(exact_gate, workflow)
        for evidence in (
            'radcra-web-store-v${release_version}.zip',
            'radcra-web-store-v${release_version}.report.json',
            'radcra-web-store-v${release_version}.zip.sha256',
            "radcra-promo-440x280.png",
            "radcra-screenshot-1280x800.png",
            "RELEASE_NOTES.md",
            "SHA256SUMS",
        ):
            self.assertIn(evidence, workflow)
        self.assertIn('cp "$GITHUB_WORKSPACE/store-assets/radcra-promo-440x280.png" "$artifacts/"', workflow)
        self.assertIn('cp "$GITHUB_WORKSPACE/store-assets/radcra-screenshot-1280x800.png" "$artifacts/"', workflow)
        self.assertIn('--build-commit "$BUILD_COMMIT"', workflow)
        self.assertNotIn("cp \"$GITHUB_WORKSPACE/store-assets/radcra-promo-440x280.png\" extension/dist", workflow)
        self.assertNotIn("cp \"$GITHUB_WORKSPACE/store-assets/radcra-screenshot-1280x800.png\" extension/dist", workflow)

    def test_local_release_script_packages_canonical_repository_and_build_commit(self):
        script = (ROOT / "deploy/scripts/release-pilot-extension.sh").read_text(encoding="utf-8")
        self.assertIn('--repository "radicalmove/radcra"', script)
        self.assertIn('--build-commit "$BUILD_COMMIT"', script)
        self.assertNotIn("radicalmove/Beta-testing-app", script)

    def readiness_fixture(self, target: Path, *, screenshot: bool = False):
        for relative in ("README.md", "docs/privacy-policy.md", "docs/chrome-web-store-listing.md", "docs/chrome-web-store-reviewer-guide.md", "site/index.html", "site/privacy/index.html", "site/support/index.html", "site/latest.json", "store-assets/README.md", "store-assets/radcra-promo-440x280.png", "extension/public/manifest.json", "tests/fixtures/store-public-key.txt"):
            source = ROOT / relative
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        (target / "extension/package.json").write_text('{"version":"0.5.36"}\n')
        if screenshot:
            Image.new("RGB", (1280, 800), "white").save(target / "store-assets/radcra-screenshot-1280x800.png")
        dist = target / "dist"
        (dist / "icons").mkdir(parents=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
        (dist / "background.js").write_text(f"/* build {commit} service https://fld-mini.tail4ccaba.ts.net */\n")
        (dist / "content.js").write_text(f"/* build {commit} */\n")
        for size in (16, 48, 128):
            shutil.copy2(ROOT / f"extension/public/icons/icon{size}.png", dist / f"icons/icon{size}.png")
        manifest = json.loads((target / "extension/public/manifest.json").read_text())
        manifest.update(version="0.5.36", host_permissions=["https://my.uconline.ac.nz/*", "https://fld-mini.tail4ccaba.ts.net/*", "https://radicalmove.github.io/radcra/*"], optional_host_permissions=["https://packages.articulateusercontent.com/*"])
        manifest["content_scripts"][0]["matches"] = ["https://my.uconline.ac.nz/*"]
        (dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        package = target / "radcra.zip"
        package_store(dist, package, "0.5.36", "radicalmove/radcra", commit)
        checksum = target / "radcra.zip.sha256"
        checksum.write_text(f"{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}\n")
        return report_path_for(package), checksum

    def run_readiness(self, root: Path, report: Path, checksum: Path, mode="fixture", screenshot=None):
        command = ["python3", str(ROOT / "deploy/scripts/store_readiness.py"), "--mode", mode, "--root", str(root), "--package-report", str(report), "--checksum", str(checksum)]
        if screenshot is not None:
            command.extend(["--screenshot", str(screenshot)])
        result = subprocess.run(command, text=True, capture_output=True)
        return result, json.loads(result.stdout)

    def test_fixture_readiness_allows_only_manual_screenshot_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "seed").write_text("seed")
            subprocess.run(["git", "add", "seed"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
            report, checksum = self.readiness_fixture(root)
            result, output = self.run_readiness(root, report, checksum)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(output), ["schema_version", "mode", "ready", "manual_screenshot_required", "checks", "errors"])
            self.assertTrue(output["ready"])
            self.assertTrue(output["manual_screenshot_required"])
            self.assertEqual(list(output["checks"]), ["identity", "public_site", "privacy_disclosure", "support", "promo", "screenshot", "package", "checksum", "production_inputs"])
            self.assertFalse(output["checks"]["screenshot"])
            self.assertFalse(output["checks"]["production_inputs"])
            self.assertEqual(output["errors"], ["screenshot_missing"])

    def test_submission_rejects_fixture_key_and_requires_all_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "seed").write_text("seed")
            subprocess.run(["git", "add", "seed"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
            report, checksum = self.readiness_fixture(root, screenshot=True)
            result, output = self.run_readiness(root, report, checksum, "submission")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output["ready"])
            self.assertFalse(output["checks"]["production_inputs"])
            self.assertEqual(output["errors"], sorted(output["errors"]))
            self.assertIn("production_public_key_not_unique", output["errors"])

    def test_readiness_rejects_every_non_runtime_zip_member(self):
        for unexpected in ("listing-art.png", "README.txt", "SOURCE.MAP"):
            with self.subTest(unexpected=unexpected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                subprocess.run(["git", "init", "-q"], cwd=root, check=True)
                subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
                subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
                (root / "seed").write_text("seed")
                subprocess.run(["git", "add", "seed"], cwd=root, check=True)
                subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
                report_path, checksum = self.readiness_fixture(root)
                archive_path = root / "radcra.zip"
                with zipfile.ZipFile(archive_path) as archive:
                    members = {name: archive.read(name) for name in archive.namelist()}
                members[unexpected] = b"unexpected"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    for name, contents in sorted(members.items()):
                        archive.writestr(name, contents)
                report = json.loads(report_path.read_text())
                report["files"] = sorted([*report["files"], unexpected])
                report["zip_sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
                report_path.write_text(json.dumps(report))
                checksum.write_text(f"{report['zip_sha256']}  {archive_path.name}\n")
                result, output = self.run_readiness(root, report_path, checksum)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output["checks"]["package"])
                self.assertIn("package_invalid", output["errors"])

    def test_readiness_independently_rejects_tampered_report_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "seed").write_text("seed")
            subprocess.run(["git", "add", "seed"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
            report_path, checksum = self.readiness_fixture(root)
            report = json.loads(report_path.read_text())
            report["review_service_origin"] = "https://different.valid-service.nz"
            report_path.write_text(json.dumps(report))
            result, output = self.run_readiness(root, report_path, checksum)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output["checks"]["package"])
            self.assertIn("package_invalid", output["errors"])

    def test_readiness_independently_rejects_archived_runtime_commit_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "seed").write_text("seed")
            subprocess.run(["git", "add", "seed"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
            report_path, checksum = self.readiness_fixture(root)
            archive_path = root / "radcra.zip"
            with zipfile.ZipFile(archive_path) as archive:
                members = {name: archive.read(name) for name in archive.namelist()}
            members["content.js"] = b"/* runtime diagnostic removed */\n"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name, contents in sorted(members.items()):
                    archive.writestr(name, contents)
            report = json.loads(report_path.read_text())
            report["zip_sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            report_path.write_text(json.dumps(report))
            checksum.write_text(f"{report['zip_sha256']}  {archive_path.name}\n")
            result, output = self.run_readiness(root, report_path, checksum)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output["checks"]["package"])
            self.assertIn("package_invalid", output["errors"])

    def test_readiness_rejects_service_origin_missing_from_archived_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "seed").write_text("seed")
            subprocess.run(["git", "add", "seed"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
            report_path, checksum = self.readiness_fixture(root)
            archive_path = root / "radcra.zip"
            with zipfile.ZipFile(archive_path) as archive:
                members = {name: archive.read(name) for name in archive.namelist()}
            members["background.js"] = members["background.js"].replace(b"https://fld-mini.tail4ccaba.ts.net", b"https://other-service.govt.nz")
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name, contents in sorted(members.items()):
                    archive.writestr(name, contents)
            report = json.loads(report_path.read_text())
            report["zip_sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            report_path.write_text(json.dumps(report))
            checksum.write_text(f"{report['zip_sha256']}  {archive_path.name}\n")
            result, output = self.run_readiness(root, report_path, checksum)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output["checks"]["package"])
            self.assertIn("package_invalid", output["errors"])

    def test_readiness_fails_closed_when_root_fixture_public_key_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "fixture@example.test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
            (root / "seed").write_text("seed")
            subprocess.run(["git", "add", "seed"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
            report_path, checksum = self.readiness_fixture(root)
            (root / "tests/fixtures/store-public-key.txt").unlink()
            result, output = self.run_readiness(root, report_path, checksum)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output["checks"]["production_inputs"])
            self.assertIn("fixture_public_key_missing", output["errors"])


if __name__ == "__main__":
    unittest.main()
