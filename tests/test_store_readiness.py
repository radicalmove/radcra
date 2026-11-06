import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import yaml
from PIL import Image, ImageChops
from deploy.scripts.store_package import package_store, report_path_for


ROOT = Path(__file__).resolve().parents[1]
PROMO_SHA256 = "9ef1de122a1b727e73be0b0a7cc446d74349380a13afcc0584d5294037013cfd"
FONT_SHA256 = "e6476c1b80502924294eed40894c5b18e06c181444ca953e5334262df9c27724"
ICON_SHA256 = {
    16: "5ffb1442092f32173ec4aafa4546948fac848a022b4025e8af83a5993725fcc2",
    48: "3d096180543c5c40d7e3d68a33b55adec18f0e6ab29f084aa4c33e1a11394d8b",
    128: "35eb036f146241984767a44dd3d53166daa085ddcdd058b3f0025fe280663b33",
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
            self.assertEqual((left, top, right, bottom), (16, 16, 112, 112))

    def test_promo_is_deterministic_approved_png_with_documented_provenance(self):
        promo = ROOT / "store-assets" / "sphere-promo-440x280.png"
        self.assertEqual(hashlib.sha256(promo.read_bytes()).hexdigest(), PROMO_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / promo.name
            self.run_generator("generate-store-assets.py", "--output", str(output))
            first = output.read_bytes()
            # The approved upload is hash-locked above. FreeType builds can
            # rasterise the same bundled font differently across platforms.
            with Image.open(promo) as approved, Image.open(output) as regenerated:
                diff = ImageChops.difference(approved, regenerated)
                self.assertLessEqual(sum(pixel != (0, 0, 0) for pixel in diff.getdata()), approved.width * approved.height * .02)
            self.run_generator("generate-store-assets.py", "--output", str(output))
            self.assertEqual(first, output.read_bytes())
        with Image.open(promo) as image:
            self.assertEqual(image.size, (440, 280))
            self.assertEqual(image.mode, "RGB")

        generator = (ROOT / "scripts" / "generate-store-assets.py").read_text()
        bundled_font = ROOT / "store-assets" / "source" / "DejaVuSans-Bold.ttf"
        self.assertTrue(bundled_font.is_file())
        self.assertEqual(hashlib.sha256(bundled_font.read_bytes()).hexdigest(), FONT_SHA256)
        self.assertIn('FONT = ROOT / "store-assets" / "source" / "DejaVuSans-Bold.ttf"', generator)
        self.assertIn(f'FONT_SHA256 = "{FONT_SHA256}"', generator)
        self.assertNotIn("FONT_CANDIDATES", generator)
        self.assertNotIn("/System/Library/Fonts", generator)
        self.assertNotIn("/usr/share/fonts", generator)
        self.assertIn('"Sphere"', generator)
        self.assertIn('"Course Review App"', generator)
        for forbidden in ("University of Canterbury", "Google", "Chrome Web Store"):
            self.assertNotIn(forbidden, generator)

        source_notes = (ROOT / "store-assets" / "source" / "README.md").read_text()
        upload_notes = (ROOT / "store-assets" / "README.md").read_text()
        self.assertRegex(source_notes.lower(), r"provenance|generated")
        self.assertRegex(source_notes.lower(), r"font")
        self.assertRegex(source_notes, r"DejaVu Fonts 2\.37")
        self.assertRegex(source_notes, r"Sphere")
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
        artifacts = '$RUNNER_TEMP/sphere-release-assets'
        exact_gate = '''python3 deploy/scripts/store_readiness.py --mode submission --root "$GITHUB_WORKSPACE" --package-report "$artifacts/sphere-web-store-v${release_version}.report.json" --checksum "$artifacts/sphere-web-store-v${release_version}.zip.sha256" --screenshot "$GITHUB_WORKSPACE/store-assets/sphere-screenshot-1280x800.png"'''
        self.assertIn(artifacts, workflow)
        self.assertIn(exact_gate, workflow)
        for evidence in (
            'sphere-web-store-v${release_version}.zip',
            'sphere-web-store-v${release_version}.report.json',
            'sphere-web-store-v${release_version}.zip.sha256',
            "sphere-promo-440x280.png",
            "sphere-screenshot-1280x800.png",
            "RELEASE_NOTES.md",
            "SHA256SUMS",
        ):
            self.assertIn(evidence, workflow)
        self.assertIn('cp "$GITHUB_WORKSPACE/store-assets/sphere-promo-440x280.png" "$artifacts/"', workflow)
        self.assertIn('cp "$GITHUB_WORKSPACE/store-assets/sphere-screenshot-1280x800.png" "$artifacts/"', workflow)
        self.assertIn('--build-commit "$BUILD_COMMIT"', workflow)
        self.assertNotIn("cp \"$GITHUB_WORKSPACE/store-assets/sphere-promo-440x280.png\" extension/dist", workflow)
        self.assertNotIn("cp \"$GITHUB_WORKSPACE/store-assets/sphere-screenshot-1280x800.png\" extension/dist", workflow)

    def test_local_release_script_packages_canonical_repository_and_build_commit(self):
        script = (ROOT / "deploy/scripts/release-pilot-extension.sh").read_text(encoding="utf-8")
        self.assertIn('--repository "radicalmove/radcra"', script)
        self.assertIn('--build-commit "$BUILD_COMMIT"', script)
        self.assertNotIn("radicalmove/Beta-testing-app", script)

    def readiness_fixture(self, target: Path, *, screenshot: bool = False):
        for relative in ("README.md", "docs/privacy-policy.md", "docs/chrome-web-store-listing.md", "docs/chrome-web-store-reviewer-guide.md", "site/index.html", "site/privacy/index.html", "site/support/index.html", "site/latest.json", "store-assets/README.md", "store-assets/sphere-promo-440x280.png", "extension/public/manifest.json", "tests/fixtures/store-public-key.txt"):
            source = ROOT / relative
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix in {".html", ".json", ".md"}:
                # Keep this isolated fixture aligned with the current Sphere
                # public contract while preserving the technical repository
                # identifier used in immutable release metadata.
                contents = source.read_text(encoding="utf-8")
                contents = contents.replace("RADCRA", "Sphere")
                contents = contents.replace("radicalmove.github.io/radcra", "radicalmove.github.io/sphere")
                contents = contents.replace("radcra-web-store", "sphere-web-store")
                contents = contents.replace("radcra-promo", "sphere-promo")
                contents = contents.replace("radcra-screenshot", "sphere-screenshot")
                destination.write_text(contents, encoding="utf-8")
            else:
                shutil.copy2(source, destination)
        (target / "extension/package.json").write_text('{"version":"0.5.36"}\n')
        if screenshot:
            Image.new("RGB", (1280, 800), "white").save(target / "store-assets/sphere-screenshot-1280x800.png")
        dist = target / "dist"
        (dist / "icons").mkdir(parents=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
        (dist / "background.js").write_text(f"/* build {commit} service https://fld-mini.tail4ccaba.ts.net */\n")
        (dist / "content.js").write_text(f"/* build {commit} */\n")
        for size in (16, 48, 128):
            shutil.copy2(ROOT / f"extension/public/icons/icon{size}.png", dist / f"icons/icon{size}.png")
        manifest = json.loads((target / "extension/public/manifest.json").read_text())
        manifest.update(version="0.5.36", host_permissions=["https://my.uconline.ac.nz/*", "https://fld-mini.tail4ccaba.ts.net/*", "https://radicalmove.github.io/sphere/*"], optional_host_permissions=["https://packages.articulateusercontent.com/*"])
        manifest["content_scripts"][0]["matches"] = ["https://my.uconline.ac.nz/*"]
        (dist / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        for path in (ROOT / "extension/public/fonts").iterdir():
            if path.suffix == ".ttf" or path.name == "OFL.txt":
                (dist / "fonts").mkdir(exist_ok=True)
                shutil.copy2(path, dist / "fonts" / path.name)
        for name in ("sphere-controls.html", "sphere-controls.js"):
            shutil.copy2(ROOT / "extension/public" / name, dist / name)
        package = target / "sphere.zip"
        package_store(dist, package, "0.5.36", "radicalmove/radcra", commit)
        checksum = target / "sphere.zip.sha256"
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
                archive_path = root / "sphere.zip"
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
            archive_path = root / "sphere.zip"
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
            archive_path = root / "sphere.zip"
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
