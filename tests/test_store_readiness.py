import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PROMO_SHA256 = "c03543f676f3d8e8fce283e451c9bc4f5f84e9b65ce37d246dd1ef8d2e6bd113"
FONT_SHA256 = "e6476c1b80502924294eed40894c5b18e06c181444ca953e5334262df9c27724"
ICON_SHA256 = {
    16: "a0455d93e95600050598f66ce434e7b9582b7c029cee1544bd73fcada897ec07",
    48: "926aa0c6ded2b75ff445cacbde0471addb873b6cd58d76655d519afda5225df7",
    128: "5b8003939258729c684fbf8264de2d3e2cbc90f5bca665f2e0c76d78a1ba9b1d",
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


if __name__ == "__main__":
    unittest.main()
