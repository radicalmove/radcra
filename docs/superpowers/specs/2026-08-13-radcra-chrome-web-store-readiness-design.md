# RADCRA Chrome Web Store Readiness Design

**Date:** 2026-08-13  
**Target release:** 0.5.35  
**Status:** Approved for implementation

## Goal

Prepare RADCRA for submission as a private Chrome Web Store beta while preserving the existing GitHub/unpacked pilot path and all course-review behaviour.

## Scope and non-goals

The release adds the package, disclosure, listing, and validation material needed for a private Chrome Web Store submission. It does not change comment storage, Moodle navigation, SCORM navigation, or the review-service protocol. It does not attempt to self-replace an unpacked extension: Chrome only provides browser-managed updates for a Web Store-installed item.

The same production build remains loadable from `extension/dist` for local pilot testing. GitHub release instructions explain both paths, with the private Web Store item recommended for testers once approved.

## Design

### 1. Store-facing identity and package assets

- Change the store-facing name to `RADCRA — Course Review (BETA)` and make the short description explicitly describe the single purpose: reviewing configured Moodle course pages with comments, highlights, and review markers.
- Add square PNG icons at 16, 48, and 128 pixels to the extension package and reference them from the generated production manifest. Keep the icon artwork aligned with the existing teal comment-marker visual and do not introduce a remote asset dependency.
- Keep the canonical extension version in `extension/package.json` and its lockfile, bumping both from 0.5.34 to 0.5.35. The generated manifest must contain the same version; the public manifest remains a `0.0.0` placeholder.
- Keep the stable public extension key/build identity unchanged so existing pilot installations retain their extension ID. Do not add a private key to the repository or package.

### 2. Privacy, disclosure, and first-run consent

- Add a public privacy-policy document under `docs/` that names the data RADCRA handles: reviewer identity and email, authentication/session material, Moodle/course/page URLs and titles, selected page text, comments/replies/status, optional screenshots, and operational logs. It will explain purpose, service recipients, retention/deletion controls, HTTPS transport, token storage boundaries, and support contact.
- Add a prominent in-product disclosure in the first-run/access flow before an account invitation, sign-in, course lookup, comment, highlight, or screenshot request is submitted. The disclosure will state what is collected, why it is needed for course review, where it is sent, and link to the policy. A user must explicitly continue; declining leaves the reviewer signed out and does not block ordinary Moodle browsing.
- Store only a versioned acknowledgement flag in extension storage. A policy-version change invalidates the previous acknowledgement and requires acknowledgement again. No credentials or course data are stored as part of the acknowledgement record.
- Keep API credentials in the existing background/storage boundaries and continue omitting dashboard cookies from API requests. The disclosure copy must accurately reflect the existing implementation rather than promising data minimisation that the code does not provide.

### 3. Private-beta listing and reviewer material

- Add a store-listing guide containing the exact title, concise description, detailed description, single purpose, permission justifications, privacy-practices answers, category suggestion, support URL, privacy-policy URL, and private-beta distribution instructions.
- Add a reviewer test guide with the test Moodle URL pattern, how to grant optional SCORM/Rise access, how to sign in using a supplied pilot account, how to create a text highlight/area marker, how to navigate a comment, and how to sign out. The guide will say that the item is a private beta for approved reviewers and will not include real credentials in the repository.
- State clearly that the Web Store installation is the update path for testers. The GitHub release page remains the fallback for development builds and manual unpacked testing.

### 4. Build and release validation

- Add a deterministic store-package validation test/script that checks:
  - generated manifest version matches package and lock versions;
  - the beta name/description and required icon paths are present;
  - the package contains no placeholder origins, private key, source maps, or remotely hosted executable code;
  - only the documented permissions/host patterns are present;
  - the privacy-policy and listing/reviewer documents exist;
  - the ZIP has `manifest.json` at its root and includes the generated extension assets.
- Extend existing build/package tests rather than duplicating manifest validation logic. The production build must continue to require HTTPS service/Moodle/Rise hosts and a real public key.
- Bump the release to 0.5.35, run extension tests, typecheck, build, deployment-package tests, and the existing immutable release script. Record checksums and release metadata in the normal external `Beta Testing App-pilot-builds/releases/` output.

## Data flow and failure handling

The first-run disclosure is local UI state. It must not make network requests merely to display the policy. If storage is unavailable or the acknowledgement record is malformed, RADCRA treats the user as not acknowledged and shows the disclosure again. If the privacy-policy link cannot open, the user may still read the embedded summary but cannot continue until they explicitly acknowledge.

Store-package validation fails closed with actionable messages. Release publication is refused if the source tree is dirty, the production build contains placeholders, the package identity changes unexpectedly, or checksums do not match. Existing pilot release safety checks remain authoritative.

## Testing

- Unit tests for manifest identity, icon references, privacy acknowledgement parsing/version invalidation, and disclosure gating.
- Package tests for ZIP layout, required assets, forbidden files/strings, and generated manifest metadata.
- Existing extension tests, typecheck, build, server tests, deployment-package tests, and release-artifact verification.
- Manual pre-submission checklist using a fresh Chrome profile: install the private beta package, confirm permission prompts, verify disclosure before sign-in, exercise Moodle and SCORM review flows, confirm optional permission prompts, and confirm a second Web Store version is offered as a browser-managed update.

## Acceptance criteria

1. A production 0.5.35 package passes the local store-package validator and the existing release gates.
2. The package has valid icons, beta-labelled identity, complete privacy/listing/reviewer documentation, and no private or remote executable material.
3. A fresh install cannot submit reviewer/course/comment data until the versioned disclosure is acknowledged.
4. Existing pilot behaviour and extension ID remain unchanged.
5. The external release folder contains the verified unpacked build, versioned ZIP, stable ZIP alias, checksums, and immutable release metadata.
