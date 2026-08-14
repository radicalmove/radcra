import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PublicReleaseSiteTests(unittest.TestCase):
    def test_public_pages_and_metadata(self):
        page = (ROOT / "site/download/index.html").read_text()
        self.assertIn("THIS EXTENSION IS FOR BETA TESTING", page)
        self.assertIn("/Beta-testing-app/privacy/", page)
        self.assertIn("github.com/radicalmove/Beta-testing-app/issues", page)
        metadata = json.loads((ROOT / "site/latest.json").read_text())
        self.assertEqual(metadata["schema_version"], 1)
        self.assertEqual(metadata["version"], "0.5.35")
        for key in ("release_url", "download_url"):
            self.assertTrue(metadata[key].startswith("https://"))

    def test_workflows_have_pages_permissions_and_release_secrets(self):
        pages = (ROOT / ".github/workflows/pages.yml").read_text()
        release = (ROOT / ".github/workflows/release-extension.yml").read_text()
        self.assertIn("actions/deploy-pages@v4", pages)
        self.assertIn("pages: write", pages)
        self.assertIn("id-token: write", pages)
        for value in ("EXTENSION_PRIVATE_KEY_PEM", "REVIEW_SERVICE_ORIGIN", "actions/deploy-pages@v4", "npm test", "python3 -m pytest -q"):
            self.assertIn(value, release)

if __name__ == "__main__": unittest.main()
