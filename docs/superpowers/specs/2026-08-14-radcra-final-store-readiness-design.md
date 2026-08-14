# RADCRA final Chrome Web Store readiness design

**Date:** 14 August 2026  
**Status:** Approved by the user  
**Scope:** Complete the local compliance, public-site, Store-artwork, package-validation, and submission-documentation work required before a private trusted-testers submission. Account-level GitHub and Google actions remain manual.

## Goal

Prepare RADCRA for a low-risk first submission to the Chrome Web Store as a private beta. The submitted product will be named **RADCRA - Course Review App (BETA)** and will clearly disclose its single purpose, data practices, permissions, beta status, reviewer requirements, and support path. The repository and public URL family will use the lowercase name `radcra`.

The final local result must be internally consistent, testable, and ready for the operator to rename and push the GitHub repository, enable GitHub Pages, configure production secrets, create the Store item, enter reviewer credentials, and submit it for review.

## Stable identity and URLs

- Store and extension name: `RADCRA - Course Review App (BETA)`.
- Repository target name: `radcra`.
- Public homepage: `https://radicalmove.github.io/radcra/`.
- Privacy policy: `https://radicalmove.github.io/radcra/privacy/`.
- Support page: `https://radicalmove.github.io/radcra/support/`.
- Update metadata: `https://radicalmove.github.io/radcra/latest.json`.
- Public contact and data-controller email: `rcadavies@gmail.com`.

The extension signing identity and accepted pilot extension ID remain unchanged. Renaming the GitHub repository must not create a second extension identity. The operator will compare the Chrome Web Store Item ID with the existing unpacked extension ID before submission.

## Compliance and disclosure model

RADCRA keeps its existing versioned, fail-closed policy acknowledgement. Before the current policy version is acknowledged, the extension must not resolve courses, authenticate, renew credentials, register SCORM launches, fetch comment data, or send Moodle/course/page data to the review service. The disclosure remains inside the extension UI and requires the user to choose Continue explicitly.

The prominent disclosure, privacy policy, Store detailed description, Privacy dashboard answers, support page, and reviewer guide must describe the same data practices:

- reviewer identity, name, email, role, approval state, and authentication/session material;
- Moodle, course, activity, page, SCORM URLs, identifiers, titles, and current location;
- selected website text, visual anchors, comments, replies, statuses, and timestamps;
- optional screenshots and attachments submitted only at the reviewer's request;
- proportionate browser/build, navigation, reliability, and error diagnostics;
- a fixed metadata-only request to GitHub Pages for update information.

The GitHub Pages update request sends no Moodle content, comments, review credentials, or review-service tokens. GitHub can receive ordinary HTTPS request metadata such as IP address and user agent under its own privacy terms. User-initiated visits to the public support page or GitHub links are separate browser navigation.

Authorised course-team members can read submitted review comments and their saved context because collaborative review is the extension's disclosed user-facing purpose. Service operators do not routinely read review content. Operator access is limited to a user's explicit request concerning specific data, security or abuse investigation, legal obligations, or aggregated and anonymised internal operations. Data is not sold, used for advertising, transferred to data brokers, or used for creditworthiness.

The Store description must prominently explain that course/page browsing context and website content are collected only to place and reopen contextual review comments. A new policy version must force a fresh acknowledgement before changed practices take effect.

## Permission alignment

The submitted manifest and Store dashboard must describe the exact same required permissions:

- `identity`: open the reviewer authentication flow and validate its exact callback;
- `storage`: keep the bounded session/reconnect state, review preferences, optional-host coordination state, and policy acknowledgement;
- `scripting`: register or inject the packaged review content script into approved optional embedded activity hosts;
- `webNavigation`: observe trusted top-level navigation and enumerate the current tab's frame hierarchy for exact embedded-course coordination.

Required host permissions are limited to the configured Moodle origin, configured HTTPS review-service origin, and `https://radicalmove.github.io/radcra/*`. Optional host permissions are limited to explicitly configured Rise/SCORM patterns. The extension must not request `tabs`, `<all_urls>`, `downloads`, or unused future permissions. It must not execute remote code. The fixed GitHub Pages response is strictly validated version metadata and never controls executable behaviour.

## Public site and support

The GitHub Pages artifact will include a self-contained homepage, privacy page, support page, download instructions, and exact update metadata. All pages use the permanent URL family and public contact email. The support page explains how to report a problem without posting access tokens, invitation codes, private Moodle links, private course content, or real student data. It offers email as the primary support route; GitHub links may be provided for public technical material but are not the sole support channel.

`latest.json` has exactly these five keys and no others:

| Key | Required value |
| --- | --- |
| `schema_version` | integer `1` |
| `version` | canonical three-component Chromium version string matching the tagged extension package |
| `release_url` | HTTPS URL `https://github.com/radicalmove/radcra/releases/tag/v<version>` |
| `download_url` | HTTPS URL `https://radicalmove.github.io/radcra/` |
| `published_at` | UTC ISO 8601 timestamp ending in `Z` |

The extension treats a missing key, extra key, wrong type, non-HTTPS URL, invalid semantic version, invalid timestamp, downgrade, network error, non-success response, or rate limit as a retryable metadata-check failure. It never follows `download_url` automatically and never evaluates metadata as code.

The release and Pages workflows must use the target repository path and publish the committed `site/` directory. Submission readiness remains false until the homepage, privacy policy, support page, and update metadata each return a successful unauthenticated HTTPS response and the update metadata passes its exact schema validation.

Repository renaming, remote URL changes, pushing, Pages configuration, DNS configuration, secret creation, and Store publication are external mutations and will not be performed automatically as part of this implementation.

## Store artwork

The existing RADCRA visual identity is retained.

- The packaged 128x128 PNG keeps the visible mark within Google's recommended 96x96 square, with approximately 16 transparent pixels on every side. The 16px and 48px runtime icons remain recognisable and visually consistent.
- The Store package continues to include valid 16px, 48px, and 128px RGBA PNG icons.
- One current 1280x800 Store screenshot shows the real extension on the authorised test Moodle course. It highlights the review overlay, course context, and a contextual marker. Unnecessary personal, private-course, credential, token, or student information is cropped, obscured, replaced, or absent.
- One 440x280 PNG promotional tile uses the RADCRA icon and established teal/red palette. It is uncluttered, readable when reduced, contains no Google or university branding, and avoids exaggerated claims.
- Final upload assets and any maintainable deterministic source belong under `store-assets/`. Generated Store artwork is not included in the extension ZIP unless the manifest requires it.

The screenshot is evidence of actual product behaviour, not a fabricated interface. Sanitisation must not alter the represented functionality.

The user has authorised screenshot capture from the currently signed-in Chrome test session. Implementation may inspect and capture the visible test page without reading, recording, or exposing account credentials. The final image is accepted only after inspection confirms that it contains no real student data, tokens, invitation details, private email addresses, or unnecessary account identifiers. If no suitable authorised test page is available during implementation, the code/docs/artwork work may be locally complete but the screenshot remains an explicit manual submission-readiness gate; a fabricated product screenshot must not be substituted.

## Packaging and release validation

The Web Store ZIP remains separate from the nested unpacked pilot ZIP. Its `manifest.json` is at the archive root. The Store package validator must reject:

- placeholder hosts, placeholder signing identity, or a placeholder build commit;
- private keys, PEM files, credentials, tokens, source maps, release reports, or unexpected release metadata;
- missing manifest assets or invalid icon dimensions/padding;
- remote executable references or dynamic execution of fetched data;
- the former `Beta-testing-app` URL family, the former university support email, or inconsistent extension identity;
- missing or incorrectly sized mandatory Store artwork in the release workspace.

The generated extension package contains runtime extension files only. Store listing screenshots and promotional tiles are separate release assets for dashboard upload.

Artwork/release validation has two explicit modes:

- **Fixture readiness:** requires the corrected packaged icons, 440x280 promotional tile, compliant public files, documentation, and a valid production-shaped fixture ZIP. It validates a screenshot when one is present but records `manual_screenshot_required` rather than failing when the authorised Chrome page was unavailable.
- **Submission readiness:** requires the sanitised 1280x800 real-product screenshot in addition to every fixture-readiness artifact. It also requires the exact production ZIP and checksum. Missing artwork or any fixture/production marker fails this mode.

The extension ZIP validator never expects listing artwork inside the ZIP. A separate release-workspace validator owns screenshot and promotional-tile checks and produces the readiness result.

Local automation distinguishes public production inputs from the signing secret:

- `MOODLE_HOST_PATTERNS`: public production Moodle match patterns included in the manifest;
- `OPTIONAL_FRAME_PATTERNS`: public optional Rise/SCORM match patterns included in the manifest;
- `REVIEW_SERVICE_ORIGIN`: public HTTPS service origin included in host permissions;
- `EXTENSION_PUBLIC_KEY`: public SPKI value included in the manifest to preserve the accepted extension ID;
- `BUILD_COMMIT`: public immutable 40-character Git commit included in diagnostics;
- `EXTENSION_PRIVATE_KEY_PEM`: CI/account secret used only to derive or verify the public key and sign approved delivery artifacts; it must never enter the extension directory, ZIP, report, logs, Pages artifact, or repository.

Automated tests may build a non-uploadable production-shaped fixture using explicit example origins and an ephemeral test key. The exact Store upload package is generated only after the operator supplies the real public production inputs and the CI secret through the documented secure release workflow. Therefore local completion proves the pipeline and fixture package; public submission readiness additionally requires the exact production package, checksum, identity comparison, and manual smoke test. No task searches the filesystem for private keys.

## Submission documentation

The Store listing guide will contain exact copy for:

- name, short description, detailed description, single purpose, category, and beta wording;
- every manifest permission and host permission;
- Privacy dashboard data-type declarations and Limited Use certifications;
- privacy, homepage, support, and update URLs;
- private trusted-testers distribution;
- remote-code declaration (`No`);
- reviewer test requirements and credentials supplied out of repository.

The Privacy dashboard declaration will use this exact mapping (or the dashboard's directly equivalent renamed label if Google changes labels after this specification date):

| Dashboard data category | Selection | RADCRA data |
| --- | --- | --- |
| Personally identifiable information | Yes | reviewer name, email, role, approval and membership identifiers |
| Health information | No | RADCRA does not request personal health data; general educational course content is treated as website content |
| Financial and payment information | No | not collected |
| Authentication information | Yes | short-lived access tokens and reconnect/device credentials |
| Personal communications | Yes | reviewer comments, replies, statuses, and intentionally attached files |
| Location | No | not collected |
| Web history | Yes | configured Moodle/course/page/SCORM URLs used for contextual navigation |
| User activity | Yes | review actions and bounded navigation/reliability diagnostics needed for the feature |
| Website content | Yes | selected text, page titles, visual anchors, requested screenshots, and course context |

The dashboard will declare remote code **No** and will certify all available Limited Use statements: data is not sold; data is not used or transferred for purposes unrelated to the single purpose; data is not used or transferred for creditworthiness or lending; data is not used for personalised advertising; transfers and human access are limited to the disclosed permitted cases. The single-purpose field is: `Help an authorised reviewer record, discuss, navigate, and resolve contextual feedback on configured Moodle course pages.`

The reviewer guide will give a deterministic fresh-profile flow covering disclosure/decline, acknowledgement, authentication, Moodle review comments, area markers, exact navigation, optional Rise/SCORM permission, update status, graceful network failure, and sign-out. Credentials and private test URLs are entered only in the Chrome Web Store Test instructions field or supplied through another approved private channel.

The final pre-submission checklist will require:

1. rename the GitHub repository to `radcra` and update the local remote;
2. push the reviewed branch and enable GitHub Actions Pages deployment;
3. verify all four public endpoints over unauthenticated HTTPS;
4. supply and verify every production build input: `MOODLE_HOST_PATTERNS` and `OPTIONAL_FRAME_PATTERNS` from the approved deployment configuration; `REVIEW_SERVICE_ORIGIN` from the live HTTPS service; `EXTENSION_PUBLIC_KEY` securely derived from `EXTENSION_PRIVATE_KEY_PEM` and compared with the accepted pilot identity; and `BUILD_COMMIT` automatically derived from the exact tagged GitHub commit and checked as a full immutable hash;
5. produce and locally load the exact Store package;
6. upload the package as a private beta and compare Item ID/public key identity;
7. upload the required Store icon, screenshot, and promotional tile;
8. enter the listing, Privacy, Distribution, and Test instructions fields exactly;
9. use deferred publishing for the first review;
10. run the reviewer guide against the submitted package and supplied test account.

## Testing and acceptance

Automated tests must cover:

- canonical name, lowercase URL family, public contact, and rejection of stale public identifiers;
- public homepage/privacy/support/latest files and exact links;
- complete privacy disclosures, GitHub Pages recipient wording, intended course-team visibility, and constrained operator access;
- exact manifest permission explanations with no `tabs` mismatch;
- required Store image files, formats, dimensions, and 128px alpha-content bounds;
- deterministic Store ZIP structure and absence of forbidden material;
- exact update metadata endpoint and metadata-only behaviour;
- workflow references to the target repository path and release assets.

Existing extension, server, package, deployment, and public-site suites must remain green. TypeScript typechecking, production build validation, ZIP validation, workflow YAML parsing, and `git diff --check` must pass.

The implementation is locally complete when all required files, available artwork, tests, documentation, a production-shaped fixture package, and upload instructions are present and verified. If the authorised Chrome test page is available, the sanitised screenshot is included; otherwise it is recorded as a single manual artwork gate. It is publicly submission-ready only after the exact production package and every manual external checklist item succeed. Google retains final review discretion, so the project may claim strong policy alignment but not guaranteed approval.

## Out of scope

- Creating or paying for the Google developer account.
- Renaming or pushing the GitHub repository.
- Enabling Pages or configuring repository secrets.
- Creating trusted-tester accounts or exposing reviewer credentials.
- Uploading, submitting, publishing, or promoting the Chrome Web Store item.
- Buying or configuring a custom domain.
- Redesigning RADCRA's product interface or review workflow.
