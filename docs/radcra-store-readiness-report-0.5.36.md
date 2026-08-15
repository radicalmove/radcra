# RADCRA Chrome Web Store readiness report — 0.5.36

**Verification date:** 15 August 2026

**Production source commit:** the exact final repository commit recorded in the generated Store package report

**Scope:** production package, public-site and artwork readiness. No Chrome Web Store upload, submission, publication, tester invitation, or dashboard change was performed.

## Status

RADCRA 0.5.36 is **ready for the Chrome Web Store upload and dashboard-review stage**. The signed production build, accepted pilot identity, deterministic Store ZIP, checksum, public Pages site, privacy/support disclosures, promotional tile, and genuine 1280x800 current-product screenshot all pass the submission-mode validator.

The remaining work is external and manual: create/configure the Chrome Web Store item, enter the approved listing and privacy declarations, upload the verified ZIP and confirm its resulting Store Item ID, provide reviewer access, complete Google's review flow, and obtain release approval before publication or tester invitation.

## Policy basis

The approved design was assessed on 14 August 2026 against the current Google Chrome Web Store policy material used for this release: the Chrome Web Store Program Policies, User Data Policy and Limited Use requirements, privacy practices/dashboard declarations, remote-code requirements, permission disclosure requirements, and listing image guidance. The release documentation maps these requirements into the single-purpose statement, nine privacy-category selections, Remote code `No`, every Limited Use certification, permission/host justifications, prominent disclosure, privacy policy, support page, and reviewer instructions.

Relevant Google policy entry points recorded for the operator's final dashboard review are:

- <https://developer.chrome.com/docs/webstore/program-policies/>
- <https://developer.chrome.com/docs/webstore/program-policies/user-data-faq/>
- <https://developer.chrome.com/docs/webstore/images/>

Google may change policy wording or dashboard labels after this assessment date. The operator must compare the live dashboard and policy text before submission. Strong local alignment does not guarantee acceptance; Google retains final review discretion.

## Exact verification results

All gates were run sequentially because concurrent extension builds share `extension/dist`.

| Gate | Result |
| --- | --- |
| `cd extension && npm test` | PASS — 527 tests; 518 passed, 0 failed, 9 skipped; 24.408 s |
| `cd extension && npm run typecheck` | PASS — exit 0 |
| `cd extension && npm run build` | PASS — Vite 7.3.6; 33 modules transformed; built in 323 ms |
| `cd extension && npm audit --omit=dev --audit-level=high` | PASS — 0 vulnerabilities |
| `cd server && python3 -m pytest -q` | PASS — 213 passed in 12.91 s; 12,571 Python 3.14 deprecation warnings from FastAPI/Starlette callability checks |
| Root Store/deployment/public/release/readiness unit suites | PASS — 66 tests in 9.468 s |
| Release script preflight-only | PASS — exit 0 using `RELEASE_PREFLIGHT_ONLY=1`, `PRIVATE_KEY_PATH=/nonsecret-placeholder/radcra-store-key.pem`, and `REVIEW_SERVICE_ORIGIN=https://review.example.org`; no build or key lookup occurred |
| Authoritative stale-value scan | PASS — no stale public identity/version values in authoritative release files; remaining matches are the validator's forbidden-value list and deliberate negative/legacy test fixtures and assertions |

Two scoped defects were found and fixed test-first during the production-shaped fixture gate:

1. `tests/fixtures/store-public-key.txt` duplicated the development placeholder, so production validation correctly rejected it. It is now a distinct valid 2048-bit RSA SPKI public-only fixture, with a regression test proving it is accepted as production-shaped and remains distinct from the development placeholder.
2. `background.js` did not retain the full build commit, so Store packaging correctly rejected its runtime evidence. Background build diagnostics now retain the immutable full commit, with a regression test that failed before and passed after the fix.

## Production package evidence

The verified package was built with:

- `BUILD_MODE=production`
- `MOODLE_HOST_PATTERNS=https://my.uconline.ac.nz/*`
- `OPTIONAL_FRAME_PATTERNS=https://packages.articulateusercontent.com/*`
- `REVIEW_SERVICE_ORIGIN=https://fld-mini.tail4ccaba.ts.net`
- `EXTENSION_PUBLIC_KEY` securely derived from the protected pilot signing key and matched to the accepted pilot identity
- `BUILD_COMMIT` set to the full lowercase 40-character final repository commit

The authoritative build commit, runtime files, manifest hash, public-key hash, host patterns, review-service origin, and ZIP hash are recorded in `radcra-web-store-v0.5.36.report.json`. The separately generated `radcra-web-store-v0.5.36.zip.sha256` is verified against that exact ZIP by the submission gate.

Submission readiness result (exit 0):

```json
{"schema_version":1,"mode":"submission","ready":true,"manual_screenshot_required":false,"checks":{"identity":true,"public_site":true,"privacy_disclosure":true,"support":true,"promo":true,"screenshot":true,"package":true,"checksum":true,"production_inputs":true},"errors":[]}
```

The upload ZIP, report, and checksum are in `/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds`.

## Artwork

- Promotional tile: ready; the committed sanitised `radcra-promo-440x280.png` passes format, dimensions, metadata, and documentation checks.
- Extension icons: ready in the generated package, including the 128 px transparent-content bounds.
- Store screenshot: ready at `store-assets/radcra-screenshot-1280x800.png`; it is a genuine RADCRA 0.5.36 capture, exactly 1280×800 PNG with metadata removed, showing the live overlay and contextual marker/comment. It remains outside the extension ZIP.

## Public endpoints

The committed source targets these endpoints:

- <https://radicalmove.github.io/radcra/>
- <https://radicalmove.github.io/radcra/privacy/>
- <https://radicalmove.github.io/radcra/support/>
- <https://radicalmove.github.io/radcra/latest.json>

All four endpoints are deployed through GitHub Pages and returned successfully over unauthenticated HTTPS on 15 August 2026. `latest.json` exposes the expected 0.5.36 schema and canonical `radicalmove/radcra` links.

## Exact production inputs required

The release operator must supply and verify:

- `MOODLE_HOST_PATTERNS`: approved production Moodle HTTPS match patterns;
- `OPTIONAL_FRAME_PATTERNS`: approved optional Rise/SCORM HTTPS match patterns;
- `REVIEW_SERVICE_ORIGIN`: the live public HTTPS review-service origin;
- `EXTENSION_PUBLIC_KEY`: the production RSA SPKI public key securely derived from `EXTENSION_PRIVATE_KEY_PEM`, compared with the accepted pilot identity, and distinct from development/fixture keys;
- `BUILD_COMMIT`: the full lowercase 40-character hash automatically derived from the exact reviewed/tagged commit;
- `EXTENSION_PRIVATE_KEY_PEM`: the protected CI/account secret used only in the approved release workflow and never written to the repository, extension directory, ZIP, report, logs, or Pages artifact.

## Remaining external/manual steps

1. Create/configure the Chrome Web Store developer item, private trusted-testers distribution, listing, nine Privacy selections, Remote code `No`, Limited Use certifications, support/privacy/homepage URLs, and private Test instructions.
2. Supply reviewer credentials and private test URLs only through the Store Test instructions field or another approved private channel.
3. Upload the exact production ZIP and compare its public key and resulting Store Item ID with the accepted pilot extension identity; stop on any mismatch.
4. Run the reviewer guide against the submitted package and account, choose deferred publishing, and obtain explicit release approval before publishing or inviting testers.

The local release materials are ready; Google retains final approval authority.
