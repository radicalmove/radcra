import json
import re
import unittest
from pathlib import Path
from html.parser import HTMLParser
from hashlib import sha256
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPHERE = "https://radicalmove.github.io/sphere/"
LEGACY = "https://radicalmove.github.io/radcra/"
REPOSITORY = "https://github.com/radicalmove/radcra"


class GuideDocument(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids, self.hrefs, self.assets, self.nav_labels = [], [], [], []
        self.h1s = self.scripts = self.expected = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'a' and attrs.get('href'):
            self.hrefs.append(attrs['href'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet':
            self.assets.append(attrs['href'])
        if tag == 'img':
            self.assets.append(attrs['src'])
        if tag == 'nav':
            self.nav_labels.append(attrs.get('aria-label'))
        self.h1s += tag == 'h1'
        self.scripts += tag == 'script'
        self.expected += 'expected' in attrs.get('class', '').split()


class PublicReleaseSiteTests(unittest.TestCase):
    def test_reviewed_pdf_guides_have_verified_files_and_page_counts(self):
        manifest_path = ROOT / 'site/guides/manifest.json'
        self.assertTrue(manifest_path.is_file(), 'Reviewed guide manifest is missing')
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest['schema_version'], 1)
        self.assertEqual(manifest['extension_version'], '0.6.17')
        self.assertEqual(manifest['reviewed_on'], '2026-11-18')
        expected = {'sphere-learning-designer-quick-start.pdf': 2, 'sphere-sme-quick-start.pdf': 2,
                    'sphere-beta-tester-quick-start.pdf': 2, 'sphere-learning-designer-handbook.pdf': 19}
        self.assertEqual({d['file']: d['pages'] for d in manifest['documents']}, expected)
        for document in manifest['documents']:
            data = (manifest_path.parent / document['file']).read_bytes()
            self.assertTrue(data.startswith(b'%PDF-'))
            self.assertTrue(data.rstrip().endswith(b'%%EOF'))
            self.assertGreater(len(data), 10000)
            self.assertEqual(len(data), document['bytes'])
            self.assertEqual(sha256(data).hexdigest(), document['sha256'])

    def test_download_and_support_pages_link_all_four_pdf_guides(self):
        expected = {'sphere-learning-designer-quick-start.pdf', 'sphere-sme-quick-start.pdf',
                    'sphere-beta-tester-quick-start.pdf', 'sphere-learning-designer-handbook.pdf'}
        for relative in ('download/index.html', 'support/index.html'):
            html = (ROOT / 'site' / relative).read_text()
            guide = GuideDocument(html)
            self.assertIn('guides', guide.ids)
            self.assertEqual({Path(urlparse(href).path).name for href in guide.hrefs if href.endswith('.pdf')}, expected)
            self.assertIn('2 pages', html)
            self.assertIn('19 pages', html)

    def test_detailed_guide_has_sections_navigation_and_expected_results(self):
        guide = GuideDocument((ROOT / 'site/support/index.html').read_text())
        self.assertIn('Guide sections', guide.nav_labels)
        for section in ('getting-started', 'before-you-start', 'install', 'request-access', 'confirm-connect',
                        'returning', 'replace-pilot', 'roles', 'course-teams', 'troubleshooting', 'privacy-support'):
            self.assertIn(section, guide.ids)
            self.assertIn('#' + section, guide.hrefs)
        self.assertGreaterEqual(guide.expected, 6)
        self.assertEqual(len(guide.ids), len(set(guide.ids)))
        html = (ROOT / 'site/support/index.html').read_text()
        self.assertGreaterEqual(html.count('Send sign-in link'), 2)

    def test_guide_pages_use_valid_local_assets_and_fragments_without_scripts(self):
        for relative in ('index.html', 'download/index.html', 'support/index.html'):
            path = ROOT / 'site' / relative
            guide = GuideDocument(path.read_text())
            self.assertEqual(guide.h1s, 1, relative)
            self.assertEqual(guide.scripts, 0, relative)
            self.assertTrue(any(asset.endswith('site.css') for asset in guide.assets), relative)
            self.assertTrue(any(asset.endswith('sphere-logo.png') for asset in guide.assets), relative)
            self.assertIn('#main', guide.hrefs)
            for asset in guide.assets:
                self.assertFalse(urlparse(asset).scheme, asset)
                self.assertTrue((path.parent / asset).is_file(), asset)
            for href in guide.hrefs:
                parsed = urlparse(href)
                if not parsed.scheme and not parsed.netloc:
                    target = path if not parsed.path else path.parent / parsed.path
                    if target.is_dir():
                        target = target / 'index.html'
                    self.assertTrue(target.is_file(), href)
                    if parsed.fragment:
                        self.assertIn(parsed.fragment, GuideDocument(target.read_text()).ids, href)

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
        self.assertIn("https://chromewebstore.google.com/detail/sphere-course-review-app/mohajifpffgbmkelnpdibcebmjpjngak", combined)
        self.assertNotIn("/releases/latest/download/", combined)
        support = (ROOT / 'site/support/index.html').read_text()
        self.assertIn('id="getting-started"', support)
        for instruction in ('Request access', 'Check access', 'same Chrome profile', 'requested role'):
            self.assertIn(instruction, support)
        self.assertIn('remove the old copy', support.lower())

    def test_metadata_schema_and_canonical_download(self):
        for relative in ("site/latest.json", "site/legacy/radcra/latest.json"):
            metadata = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(set(metadata), {"schema_version", "version", "release_url", "download_url", "published_at"})
            self.assertEqual(metadata["schema_version"], 1)
            self.assertEqual(metadata["version"], "0.6.0")
            self.assertEqual(metadata["download_url"], SPHERE)
            self.assertEqual(metadata["release_url"], REPOSITORY + "/releases/tag/v0.6.0")
            self.assertRegex(metadata["published_at"], r"^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_pages_workflow_stages_exact_external_paths_with_scoped_ssh_key(self):
        workflow_path = ROOT / ".github/workflows/pages.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIsInstance(yaml.safe_load(workflow), dict)
        for value in (
            "SPHERE_PAGES_DEPLOY_KEY",
            "set +x",
            "StrictHostKeyChecking=yes",
            "https://api.github.com/meta",
            "git clone --branch main --depth 1 git@github.com:radicalmove/radicalmove.github.io.git",
            'cp -R site/. "$pages/sphere/"',
            'cp site/legacy/radcra/index.html "$pages/radcra/index.html"',
            'cp site/legacy/radcra/latest.json "$pages/radcra/latest.json"',
            'git -C "$pages" push origin main',
        ):
            self.assertIn(value, workflow)
        self.assertNotIn('SPHERE_PAGES_REPOSITORY_TOKEN', workflow)
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
