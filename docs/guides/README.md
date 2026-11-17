# Sphere published guides

Reviewed together on 18 November 2026 for extension 0.6.17 and the deployed course-access workflow.

| Document | PDF | Pages |
| --- | --- | --- |
| Learning Designer quick start | `site/guides/sphere-learning-designer-quick-start.pdf` | 2 |
| SME quick start | `site/guides/sphere-sme-quick-start.pdf` | 2 |
| Beta tester quick start | `site/guides/sphere-beta-tester-quick-start.pdf` | 2 |
| Complete Learning Designer handbook | `site/guides/sphere-learning-designer-handbook.pdf` | 19 |

Editable Word sources are retained in `docs/guides/sources/`. They are intentionally tracked exceptions to the generic DOCX ignore rule. The Pages workflow publishes only `site/`, not these source files.

## Review and verification

- Re-read all four documents together, with independent review against account/course onboarding, comment visibility, selective SME sharing, reply permissions and the actual notification worker.
- No major contradictions or public-content blockers found. Preserved the administrator-only approval boundary, LEARN versus older UCO joining routes, same-profile confirmation, approval-based expiry, hidden SME replies to beta testers, limited comment-mail pilot and temporary checklist/export limitations.
- Handbook navigation supports PDF bookmarks as well as Word. The server-specific administration address was replaced by instructions to ask the administrator. Screenshots use fictional content; no reviewer credentials, invitation codes, confirmation links or real student data are included.
- Parsed all PDFs: three two-page guides and one 19-page handbook. Searchable text, bookmarks and external link targets verified. No JavaScript, launch action or embedded-file catalog. Links target only the official Store, public Sphere site and support email.
- Handbook re-rendered with the bundled document runtime. Changed pages 1 and 19 inspected; pages 2–18 matched the previously inspected PNGs byte-for-byte. Quick-guide PDFs are the exact inspected final exports. Word accessibility audit found no issues in its covered checks.
- Final local checks: **72 root tests** and **10 desktop/mobile browser tests passed**. Browser tests checked both PDF-link sections, response MIME type and every file hash; screenshots inspected at 1280px and 390px. `git diff --check` passed.
- Two new website contract tests were observed failing before the PDF files and links were added, then passed. The root test checks manifest declarations and file hashes; actual page-count parsing was performed separately with bundled `pypdf`.

## Updating the guides

1. Edit the relevant Word source and check all four for consistent instructions. Recheck current permissions and mail behaviour rather than inferring features from earlier plans.
2. Export with the bundled document renderer. Inspect every changed page, verify unchanged pages or inspect them again, and retain the editable source. Confirm quick guides remain two pages and all links/bookmarks work.
3. Replace only the corresponding `site/guides/` PDF. Update its actual parsed page count, byte count and SHA-256 in `manifest.json`, plus the review date and relevant version references in sources, pages and tests.
4. Run the site/release tests and opt-in public-guide browser tests. Check for private content, metadata, credentials and unsupported notification promises before publication.
5. Publish through the existing Pages workflow; verify the final public PDF responses match the manifest hashes. No Chrome extension upload or live server deployment is required for a document-only update.
