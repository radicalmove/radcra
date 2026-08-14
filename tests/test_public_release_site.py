import json
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_HOME = "https://radicalmove.github.io/radcra/"
PUBLIC_PRIVACY = f"{PUBLIC_HOME}privacy/"
PUBLIC_SUPPORT = f"{PUBLIC_HOME}support/"
PUBLIC_METADATA = f"{PUBLIC_HOME}latest.json"
REPOSITORY = "https://github.com/radicalmove/radcra"


class PublicReleaseSiteTests(unittest.TestCase):
    def test_public_pages_and_metadata_have_exact_unauthenticated_urls(self):
        root_page = (ROOT / "site/index.html").read_text(encoding="utf-8")
        download_page = (ROOT / "site/download/index.html").read_text(encoding="utf-8")
        support_page = (ROOT / "site/support/index.html").read_text(encoding="utf-8")
        for page in (root_page, download_page):
            self.assertIn("RADCRA", page)
            self.assertEqual(page.count("THIS EXTENSION IS FOR BETA TESTING"), 1)
        self.assertIn(PUBLIC_PRIVACY, root_page)
        self.assertIn(PUBLIC_SUPPORT, root_page)
        self.assertIn(PUBLIC_METADATA, root_page)
        self.assertIn(REPOSITORY + "/releases/latest/download/radcra-web-store-v0.5.36.zip", root_page)
        self.assertIn(REPOSITORY + "/releases/latest/download/moodle-review-extension-v0.5.36-chrome-edge.zip", root_page)
        self.assertIn(PUBLIC_PRIVACY, support_page)
        self.assertIn('<html lang="en">', support_page)
        self.assertIn('<meta charset="utf-8">', support_page)
        self.assertIn('name="viewport"', support_page)
        self.assertIn("<title>RADCRA support</title>", support_page)
        self.assertIn('href="mailto:rcadavies@gmail.com"', support_page)
        self.assertIn('href="https://github.com/radicalmove/radcra/issues"', support_page)
        for secret in ("credentials", "tokens", "invitation codes", "private course links", "real student data", "unnecessary course content"):
            self.assertIn(secret, support_page.lower())

        metadata = json.loads((ROOT / "site/latest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(metadata), {"schema_version", "version", "release_url", "download_url", "published_at"})
        self.assertEqual(metadata["schema_version"], 1)
        self.assertRegex(metadata["version"], r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)$")
        for key in ("release_url", "download_url"):
            parsed = urlparse(metadata[key])
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.netloc)
        self.assertEqual(metadata["version"], "0.5.36")
        self.assertEqual(metadata["release_url"], REPOSITORY + "/releases/tag/v0.5.36")
        self.assertEqual(metadata["download_url"], PUBLIC_HOME)
        published = datetime.fromisoformat(metadata["published_at"].replace("Z", "+00:00"))
        self.assertIsNotNone(published.tzinfo)
        self.assertEqual(published.utcoffset(), timezone.utc.utcoffset(published))
        self.assertTrue(metadata["published_at"].endswith("Z"))

    def test_authoritative_copy_is_canonical_and_complete(self):
        paths = ["README.md", "docs/privacy-policy.md", "docs/chrome-web-store-listing.md",
                 "docs/chrome-web-store-reviewer-guide.md", "docs/releasing.md", "site/index.html",
                 "site/download/index.html", "site/privacy/index.html", "site/support/index.html", "site/latest.json"]
        combined = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("Beta-testing-app", combined)
        self.assertNotIn("richard.davies@canterbury.ac.nz", combined)
        self.assertIn("rcadavies@gmail.com", combined)
        listing = (ROOT / "docs/chrome-web-store-listing.md").read_text(encoding="utf-8")
        self.assertIn("RADCRA - Course Review App (BETA)", listing)
        self.assertIn("Remote code:** `No`", listing)
        self.assertIn("`webNavigation`", listing)
        self.assertNotRegex(listing, r"\| `tabs` \|")
        for category in ("Personally identifiable information", "Health information", "Financial and payment information", "Authentication information", "Personal communications", "Location", "Web history", "User activity", "Website content"):
            self.assertIn(category, listing)
        checklist = (ROOT / "docs/chrome-web-store-pre-submission-checklist.md").read_text(encoding="utf-8")
        for phrase in ("rename", "remote", "GitHub Pages", "MOODLE_HOST_PATTERNS", "EXTENSION_PRIVATE_KEY_PEM", "private trusted testers", "reviewer credentials", "Item ID", "screenshot", "promotional", "exact ZIP", "deferred publishing"):
            self.assertIn(phrase.lower(), checklist.lower())

    def test_five_disclosures_use_the_exact_complete_access_model(self):
        surfaces = ["extension/src/overlay/root.ts", "docs/privacy-policy.md", "docs/chrome-web-store-listing.md",
                    "docs/chrome-web-store-reviewer-guide.md", "site/privacy/index.html", "site/support/index.html"]
        required = (
            "reviewer name, email, role, and approval status",
            "authentication, session, reconnect, and device credentials",
            "activity/SCORM identifiers, titles, and current location",
            "comments, replies, statuses, timestamps, selected text, visual anchors, and optional screenshots and attachments submitted only at the reviewer's request",
            "browser/build, navigation, reliability, and error diagnostics",
            "authorised course-team members may read course-review content",
            "do not routinely read it",
            "explicit user request about that data",
            "security or abuse",
            "legal obligation",
            "aggregated and anonymised data",
            "IP address, user agent, request time, and requested path",
            "no Moodle content, review content, credentials, or tokens",
        )
        for path in surfaces:
            copy = (ROOT / path).read_text(encoding="utf-8").lower()
            for phrase in required:
                self.assertIn(phrase.lower(), copy, f"{path}: {phrase}")

    def test_exact_permission_reviewer_and_provenance_copy(self):
        listing = (ROOT / "docs/chrome-web-store-listing.md").read_text(encoding="utf-8")
        for exact in (
            "Opens the approved reviewer authentication flow and validates its exact callback.",
            "reconnect state and optional-host coordination",
            "Registers and injects the packaged content script only on approved optional embedded hosts.",
            "Observes trusted top-level navigation and enumerates the current-tab frame hierarchy.",
        ):
            self.assertIn(exact, listing)
        guide = (ROOT / "docs/chrome-web-store-reviewer-guide.md").read_text(encoding="utf-8")
        self.assertLess(guide.index("Choose **Decline**"), guide.index("Choose **Continue**"))
        for operation in ("course resolution", "authentication or renewal", "SCORM registration", "comment fetch", "Moodle-page transmission"):
            self.assertIn(operation, guide)
        checklist = (ROOT / "docs/chrome-web-store-pre-submission-checklist.md").read_text(encoding="utf-8")
        for exact in ("from the approved deployment configuration", "from the live HTTPS service",
                      "securely derived from `EXTENSION_PRIVATE_KEY_PEM` and compared with the accepted pilot identity",
                      "automatically derived from the exact tagged GitHub commit"):
            self.assertIn(exact, checklist)

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
