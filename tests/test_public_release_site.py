import json
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_HOME = "https://radicalmove.github.io/Beta-testing-app/"
PUBLIC_PRIVACY = f"{PUBLIC_HOME}privacy/"
PUBLIC_METADATA = f"{PUBLIC_HOME}latest.json"
SUPPORT = "https://github.com/radicalmove/Beta-testing-app/issues"
REPOSITORY = "https://github.com/radicalmove/Beta-testing-app"


class PublicReleaseSiteTests(unittest.TestCase):
    def test_public_pages_and_metadata_have_exact_unauthenticated_urls(self):
        root_page = (ROOT / "site/index.html").read_text(encoding="utf-8")
        download_page = (ROOT / "site/download/index.html").read_text(encoding="utf-8")
        for page in (root_page, download_page):
            self.assertIn("RADCRA", page)
            self.assertIn("THIS EXTENSION IS FOR BETA TESTING", root_page)
        self.assertIn(PUBLIC_PRIVACY, root_page)
        self.assertIn(SUPPORT, root_page)
        self.assertIn(PUBLIC_METADATA, root_page)
        self.assertIn(REPOSITORY + "/releases/latest/download/radcra-web-store-v0.5.35.zip", root_page)
        self.assertIn(REPOSITORY + "/releases/latest/download/moodle-review-extension-v0.5.35-chrome-edge.zip", root_page)

        metadata = json.loads((ROOT / "site/latest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(metadata), {"schema_version", "version", "release_url", "download_url", "published_at"})
        self.assertEqual(metadata["schema_version"], 1)
        self.assertRegex(metadata["version"], r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
        for key in ("release_url", "download_url"):
            parsed = urlparse(metadata[key])
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.netloc)
        self.assertEqual(metadata["release_url"], REPOSITORY + "/releases/tag/v0.5.35")
        self.assertEqual(metadata["download_url"], REPOSITORY + "/releases/download/v0.5.35/radcra-web-store-v0.5.35.zip")
        published = datetime.fromisoformat(metadata["published_at"].replace("Z", "+00:00"))
        self.assertIsNotNone(published.tzinfo)
        self.assertEqual(published.utcoffset(), timezone.utc.utcoffset(published))
        self.assertTrue(metadata["published_at"].endswith("Z"))

    def test_workflows_have_pages_permissions_and_release_secrets(self):
        pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        release = (ROOT / ".github/workflows/release-extension.yml").read_text(encoding="utf-8")
        self.assertIn("branches: [main]", pages)
        self.assertIn("site/**", pages)
        for value in ("actions/configure-pages@v5", "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4", "pages: write", "id-token: write"):
            self.assertIn(value, pages)
        for value in (
            "tags: ['v*.*.*']",
            "EXTENSION_PRIVATE_KEY_PEM",
            "REVIEW_SERVICE_ORIGIN",
            "BUILD_COMMIT: ${{ github.sha }}",
            "BUILD_COMMIT=${{ github.sha }}",
            "chmod 600",
            "trap cleanup EXIT",
            "rm -f -- \"$key_file\"",
            "python3 -m pip install -r scripts/requirements-build.txt",
            "python3 -m pip install -e '.[dev]'",
            "python3 -m pip install PyYAML",
            "npm ci",
            "npm test",
            "python3 -m pytest -q",
            "tests/test_public_release_site.py",
            "actions/upload-pages-artifact@v3",
            "actions/deploy-pages@v4",
            "SHA256SUMS",
            "RELEASE_NOTES.md",
        ):
            self.assertIn(value, release)
        self.assertNotIn("release-pilot-extension.sh", release)


if __name__ == "__main__":
    unittest.main()
