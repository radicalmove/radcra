import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPHERE = "https://radicalmove.github.io/sphere/"
LEGACY = "https://radicalmove.github.io/radcra/"
REPOSITORY = "https://github.com/radicalmove/radcra"


class PublicReleaseSiteTests(unittest.TestCase):
    def test_exact_six_unauthenticated_url_contracts_and_migration(self):
        pages = {
            f"{SPHERE}": ROOT / "site/index.html",
            f"{SPHERE}download/": ROOT / "site/download/index.html",
            f"{SPHERE}privacy/": ROOT / "site/privacy/index.html",
            f"{SPHERE}support/": ROOT / "site/support/index.html",
            f"{SPHERE}latest.json": ROOT / "site/latest.json",
            f"{LEGACY}latest.json": ROOT / "site/legacy/radcra/latest.json",
        }
        self.assertEqual(len(pages), 6)
        for url, path in pages.items():
            self.assertTrue(path.is_file(), url)
            parsed = urlparse(url)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "radicalmove.github.io")
        migration = (ROOT / "site/legacy/radcra/index.html").read_text(encoding="utf-8")
        self.assertIn(SPHERE, migration)
        self.assertNotIn("course", migration.lower())
        self.assertNotIn("review", migration.lower())
        self.assertNotIn("credential", migration.lower())
        self.assertNotIn("token", migration.lower())
        self.assertNotIn("executable", migration.lower())

    def test_public_pages_are_sphere_branded_and_have_one_beta_warning(self):
        paths = [ROOT / name for name in ("site/index.html", "site/download/index.html", "site/privacy/index.html", "site/support/index.html")]
        for path in paths:
            page = path.read_text(encoding="utf-8")
            self.assertIn("Sphere", page)
            self.assertEqual(page.count("THIS EXTENSION IS FOR BETA TESTING"), 1, path)
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for link in (f"{SPHERE}privacy/", f"{SPHERE}support/", f"{SPHERE}latest.json"):
            self.assertIn(link, combined)
        self.assertIn("sphere-web-store-v0.6.0.zip", combined)
        self.assertIn("moodle-review-extension-v0.6.0-chrome-edge.zip", combined)

    def test_metadata_schema_and_canonical_download(self):
        for relative in ("site/latest.json", "site/legacy/radcra/latest.json"):
            metadata = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(set(metadata), {"schema_version", "version", "release_url", "download_url", "published_at"})
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(metadata["version"], "0.6.0")
            self.assertEqual(metadata["download_url"], SPHERE)
            self.assertEqual(metadata["release_url"], REPOSITORY + "/releases/tag/v0.6.0")
            self.assertRegex(metadata["published_at"], r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_pages_workflow_stages_exact_external_paths_with_masked_token(self):
        workflow_path = ROOT / ".github/workflows/pages.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIsInstance(yaml.safe_load(workflow), dict)
        for value in (
            "SPHERE_PAGES_REPOSITORY_TOKEN",
            "set +x",
            "::add-mask::${SPHERE_PAGES_REPOSITORY_TOKEN}",
            "git -c \"http.extraheader=AUTHORIZATION: bearer ${SPHERE_PAGES_REPOSITORY_TOKEN}\" clone --branch main --depth 1 https://github.com/radicalmove/radicalmove.github.io.git",
            'cp -R site/. "$pages/sphere/"',
            'cp site/legacy/radcra/index.html "$pages/radcra/index.html"',
            'cp site/legacy/radcra/latest.json "$pages/radcra/latest.json"',
            'git -c "http.extraheader=AUTHORIZATION: bearer ${SPHERE_PAGES_REPOSITORY_TOKEN}" -C "$pages" push origin main',
        ):
            self.assertIn(value, workflow)
        self.assertNotIn("actions/deploy-pages", workflow)
        self.assertNotIn("actions/upload-pages-artifact", workflow)

    def test_current_public_docs_use_sphere_urls(self):
        paths = [
            "README.md", "docs/privacy-policy.md", "docs/chrome-web-store-listing.md",
            "docs/chrome-web-store-reviewer-guide.md", "docs/chrome-web-store-pre-submission-checklist.md",
            "docs/releasing.md", "extension/README.md", "store-assets/README.md",
        ]
        combined = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("radicalmove.github.io/radcra", combined)
        for link in (SPHERE, f"{SPHERE}privacy/", f"{SPHERE}support/", f"{SPHERE}latest.json"):
            self.assertIn(link, combined)
        listing = (ROOT / "docs/chrome-web-store-listing.md").read_text(encoding="utf-8")
        self.assertIn("Sphere - Course Review App (BETA)", listing)
        self.assertIn("author's first name", listing)
        self.assertIn("Minimise comments", listing)
        self.assertIn("Remote code:** `No`", listing)

    def test_complete_privacy_support_copy_is_present(self):
        surfaces = [ROOT / "docs/privacy-policy.md", ROOT / "site/privacy/index.html", ROOT / "site/support/index.html"]
        required = (
            "reviewer name, email, role, and approval status",
            "authentication, session, reconnect, and device credentials",
            "activity/SCORM identifiers, titles, and current location",
            "comments, replies, statuses, timestamps, selected text, visual anchors",
            "browser/build, navigation, reliability, and error diagnostics",
            "authorised course-team members may read course-review content",
            "do not routinely read it", "explicit user request about that data",
            "security or abuse", "legal obligation", "aggregated and anonymised data",
            "IP address, user agent, request time, and requested path",
            "no Moodle content, review content, credentials, or tokens",
        )
        for path in surfaces:
            copy = path.read_text(encoding="utf-8").lower()
            for phrase in required:
                self.assertIn(phrase.lower(), copy, f"{path}: {phrase}")


if __name__ == "__main__":
    unittest.main()
