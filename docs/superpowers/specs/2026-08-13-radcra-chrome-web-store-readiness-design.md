# RADCRA Chrome Web Store Readiness Design

**Date:** 2026-08-13  
**Target release:** 0.5.35  
**Status:** Approved for implementation

## Goal

Prepare RADCRA for submission as a private Chrome Web Store beta, add the requested GitHub download/update path, and preserve all course-review behaviour.

## Scope and non-goals

The release adds the package, disclosure, listing, validation, GitHub delivery, and update-notification material needed for a private Chrome Web Store submission and a maintainable developer pilot. It does not change comment storage, Moodle navigation, SCORM navigation, or the review-service protocol. It does not attempt to self-replace an unpacked extension: Chrome only provides browser-managed updates for a Web Store-installed item.

The same production build remains loadable from `extension/dist` for local pilot testing. GitHub release instructions explain both paths, with the private Web Store item recommended for testers once approved.

## Design

### 1. Store-facing identity and package assets

- Change the store-facing name to `RADCRA — Course Review (BETA)` and make the short description explicitly describe the single purpose: reviewing configured Moodle course pages with comments, highlights, and review markers.
- Add square PNG icons at 16, 48, and 128 pixels to the extension package and reference them from the generated production manifest. Keep the icon artwork aligned with the existing teal comment-marker visual and do not introduce a remote asset dependency.
- Keep the canonical extension version in `extension/package.json` and its lockfile, bumping both from 0.5.34 to 0.5.35. The generated manifest must contain the same version; the public manifest remains a `0.0.0` placeholder.
- Keep the stable public extension key/build identity unchanged so existing pilot installations retain their extension ID. Do not add a private key to the repository or package.
- Use the current production public key for the first Web Store draft upload. Before submission, compare the dashboard’s public key with the build key byte-for-byte after canonical base64/DER normalisation. If they differ, stop the submission: do not publish a second identity. Instead, deliberately choose the dashboard identity as a migration, update `EXTENSION_REDIRECT_URIS`, issue a one-time new pilot build, and document that existing unpacked installs must be replaced. All later Store and pilot packages must inject the one accepted key.

### 2. Privacy, disclosure, and first-run consent

- Add a public privacy-policy document under `docs/` that names the data RADCRA handles: reviewer identity and email, authentication/session material, Moodle/course/page URLs and titles, selected page text, comments/replies/status, optional screenshots, and operational logs. It will explain purpose, service recipients, retention/deletion controls, HTTPS transport, token storage boundaries, and support contact.
- Publish the policy at a stable unauthenticated HTTPS URL on the project’s GitHub Pages/download site, and define a stable support URL. The policy will include the literal Chrome Limited Use statement and the Web Store listing will point to this exact URL; repository copies are source material only.
- Add a prominent in-product disclosure in the first-run/access flow before an account invitation, sign-in, course lookup, comment, highlight, screenshot request, or any automatic refresh is submitted. The disclosure will state what is collected, why it is needed for course review, where it is sent, and link to the public policy. A user must explicitly continue; declining leaves the reviewer signed out and does not block ordinary Moodle browsing.
- Enforce the disclosure at the trusted background/API boundary, not only in UI: `RESOLVE_COURSE`, `LOOKUP_REVIEW_COURSE`, viewer/comment operations, SCORM launch registration, token renewal, and screenshot upload are rejected locally until the current policy version is acknowledged. On a fresh install or policy-version change, active session/device credentials are cleared from use and the reviewer must acknowledge again before authentication or renewal. Malformed acknowledgement records are treated as absent.
- Store only a versioned acknowledgement flag in extension storage. No credentials or course data are stored as part of the acknowledgement record.
- Keep API credentials in the existing background/storage boundaries and continue omitting dashboard cookies from API requests. The disclosure copy must accurately reflect the existing implementation rather than promising data minimisation that the code does not provide.

### 3. Private-beta listing and reviewer material

- Add a store-listing guide containing the exact title, concise description, detailed description, single purpose, permission justifications, privacy-practices answers, category suggestion, support URL, privacy-policy URL, and private-beta distribution instructions.
- Add a reviewer test guide with the test Moodle URL pattern, how to grant optional SCORM/Rise access, how to sign in using a supplied pilot account, how to create a text highlight/area marker, how to navigate a comment, and how to sign out. The guide will say that the item is a private beta for approved reviewers and will not include real credentials in the repository.
- State clearly that the Web Store installation is the update path for testers. The GitHub release page remains the fallback for development builds and manual unpacked testing.
- Include the exact beta disclosure text `THIS EXTENSION IS FOR BETA TESTING` in the Web Store detailed description and in the generated listing template. The extension name ends in `(BETA)`.
- Document the one-time Web Store identity sequence: upload the first ZIP as a draft, copy the dashboard public key into the production build’s `key`, compare the Web Store Item ID with the unpacked `chrome://extensions` ID, and add only the exact `chrome.identity.getRedirectURL()` value to `EXTENSION_REDIRECT_URIS`.

### 4. Build and release validation

- Add a deterministic store-package validation test/script that checks:
  - generated manifest version matches package and lock versions;
  - the beta name/description and required icon paths are present;
  - the package contains no placeholder origins, private key, source maps, or remotely hosted executable code;
  - only the documented permissions/host patterns are present;
  - the privacy-policy and listing/reviewer documents exist;
  - the Web Store ZIP has `manifest.json` at its root and includes the generated extension assets.
- Keep the existing immutable pilot ZIP layout unchanged for unpacked delivery. Add a separate root-level Web Store upload ZIP and checksum entry; do not make the current `release_artifacts.py` archive silently change shape. Copy the icons into both package forms and update artifact comparison/checksum tests accordingly.
- Extend existing build/package tests rather than duplicating manifest validation logic. The production build must continue to require HTTPS service/Moodle/Rise hosts and a real public key.
- Add a GitHub Actions release workflow triggered by `v*.*.*` tags. It runs the existing verification/build gates, creates the root-level Web Store ZIP and the unpacked pilot ZIP, publishes both plus `SHA256SUMS` and release notes to the GitHub Release, and updates a static `latest.json` endpoint. Add a GitHub Pages/download page with direct stable links and separate Web Store/private-pilot instructions.
- Add an in-extension update checker that reads exactly `https://radicalmove.github.io/Beta-testing-app/latest.json` no more than once per 24 hours and exposes a manual check in Help. The production manifest declares `https://radicalmove.github.io/*` as a host permission solely for this JSON request; the listing explains that this permission reads release metadata and never page content. The JSON schema is `{schema_version: 1, version: string, release_url: HTTPS string, download_url: HTTPS string, published_at: ISO-8601 string}`. Invalid schema, network failure, downgrade, or rate-limit responses are treated as “no update” with a retryable status and no code execution. Results are cached locally with `checkedAt`, and the checker never downloads, executes, or replaces extension code. It compares versions and links to the GitHub release/download page. It must describe unpacked updates as manual reloads; Web Store installs are updated by Chrome.

### 5. Exact public URLs and GitHub delivery

Use the repository’s GitHub Pages project site as the public home:

- Download page: `https://radicalmove.github.io/Beta-testing-app/`
- Privacy policy: `https://radicalmove.github.io/Beta-testing-app/privacy/`
- Support/issues: `https://github.com/radicalmove/Beta-testing-app/issues`
- Update metadata: `https://radicalmove.github.io/Beta-testing-app/latest.json`

The Pages workflow deploys the committed `site/` directory on pushes to `main` using `actions/configure-pages`, `actions/upload-pages-artifact`, and `actions/deploy-pages`, with `pages: write` and `id-token: write`. A CI smoke test must fetch all four URLs without authentication and validate the JSON schema for `latest.json`. The privacy policy source is kept in `docs/privacy-policy.md` and copied into `site/privacy/index.html` by the Pages content change.

The tagged release workflow uses these exact protected values: repository secret `EXTENSION_PRIVATE_KEY_PEM` (the existing production RSA PEM), repository variable `REVIEW_SERVICE_ORIGIN`, and the immutable `github.sha` as `BUILD_COMMIT`. It writes the PEM to a `mktemp` file with mode 600, derives/injects the public key during the build, and removes the file in an unconditional trap; the secret is never echoed, uploaded, or included in logs. CI uses an isolated workspace directory for the root-level Web Store ZIP and pilot ZIP, so it does not call the local external-delivery release script or depend on `Beta Testing App-pilot-builds`. Local releases continue to use the existing `PRIVATE_KEY_PATH` and external immutable delivery process.
- Bump the release to 0.5.35, run extension tests, typecheck, build, deployment-package tests, and the existing immutable release script. Record checksums and release metadata in the normal external `Beta Testing App-pilot-builds/releases/` output.

## Data flow and failure handling

The first-run disclosure is local UI state. It must not make network requests merely to display the policy. If storage is unavailable or the acknowledgement record is malformed, RADCRA treats the user as not acknowledged and shows the disclosure again. If the privacy-policy link cannot open, the user may still read the embedded summary but cannot continue until they explicitly acknowledge. Automatic background refreshes must pass the same policy gate and must not leak course/page data while the gate is closed.

Store-package validation fails closed with actionable messages. Release publication is refused if the source tree is dirty, the production build contains placeholders, the package identity changes unexpectedly, or checksums do not match. Existing pilot release safety checks remain authoritative.

## Testing

- Unit tests for manifest identity, icon references, privacy acknowledgement parsing/version invalidation, and disclosure gating.
- Package tests for ZIP layout, required assets, forbidden files/strings, and generated manifest metadata.
- Existing extension tests, typecheck, build, server tests, deployment-package tests, and release-artifact verification.
- Manual pre-submission checklist using a fresh Chrome profile: install the private beta package, confirm permission prompts, verify disclosure before sign-in, exercise Moodle and SCORM review flows, confirm optional permission prompts, and confirm a second Web Store version is offered as a browser-managed update.

## Acceptance criteria

1. A production 0.5.35 package passes the local store-package validator and the existing release gates.
2. The package has valid icons, beta-labelled identity, complete privacy/listing/reviewer documentation, and no private or remote executable material.
3. A fresh install cannot submit reviewer/course/comment data until the versioned disclosure is acknowledged; the same is true after acknowledgement invalidation, including automatic refresh and token renewal.
4. Existing feature behaviour and the accepted extension ID remain unchanged after a user acknowledges the current policy. A policy-version change intentionally shows the disclosure and pauses network activity; it does not alter comments, navigation, or stored review data, and the user can resume after acknowledgement.
5. The external release folder contains the verified unpacked build, versioned pilot ZIP, stable pilot ZIP alias, Web Store root-level ZIP, checksums, and immutable release metadata.
6. A tagged GitHub release publishes the two ZIP formats, checksums, `latest.json`, and clear download instructions; the extension’s checker reports a newer version without attempting self-installation.
7. Post-publication manual acceptance confirms the private Web Store item is visible to trusted testers, the reviewer can exercise the documented flow, and a subsequent higher version is offered as a browser-managed update. This is explicitly a dashboard/browser acceptance step, not a local automated test.
