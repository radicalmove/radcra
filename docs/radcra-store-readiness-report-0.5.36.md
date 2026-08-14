# RADCRA Chrome Web Store readiness report — 0.5.36

**Verification date:** 14 August 2026

**Fixture source commit:** `4b869c34a858cede20d35b040ec05d93482c49c3`

**Scope:** local Store-readiness evidence only; no push, tag, deployment, dashboard change, upload, submission, or private-key search was performed.

## Status

RADCRA 0.5.36 is locally **submission-shaped**, but it is **not submission-ready**. The local automated gates, compliant promotional tile, public-source files, production-shaped fixture build, deterministic Store ZIP, checksum, and fixture-mode validator pass. The fixture uses example origins and a public-only test key and must never be uploaded.

Real submission readiness remains blocked until the secure production configuration and accepted public identity are supplied, a genuine current-product screenshot is captured and sanitised, the renamed public repository and Pages site are deployed and verified, and the Chrome Web Store dashboard/tester/reviewer workflow is completed.

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

## Production-shaped fixture evidence

The fixture was built with:

- `BUILD_MODE=production`
- `MOODLE_HOST_PATTERNS=https://moodle.example.org/*`
- `OPTIONAL_FRAME_PATTERNS=https://rise.example.org/*`
- `REVIEW_SERVICE_ORIGIN=https://review.example.org`
- `EXTENSION_PUBLIC_KEY` read only from `tests/fixtures/store-public-key.txt`
- `BUILD_COMMIT=4b869c34a858cede20d35b040ec05d93482c49c3`

Package result:

```json
{"build_commit": "4b869c34a858cede20d35b040ec05d93482c49c3", "build_mode": "production", "files": ["background.js", "content.js", "icons/icon128.png", "icons/icon16.png", "icons/icon48.png", "manifest.json"], "manifest_sha256": "3d6692a20bfb97a32aa2c96d50197815e0f755c01e489c23203fb6b38dc9b923", "moodle_patterns": ["https://moodle.example.org/*"], "optional_frame_patterns": ["https://rise.example.org/*"], "public_key_sha256": "b27534c70e0ced12a3c35f2c10a199c91efbaf5c3a6063dfb6ce4e948c5195a2", "repository": "radicalmove/radcra", "review_service_origin": "https://review.example.org", "schema_version": 1, "version": "0.5.36", "zip_sha256": "e3af9e2654b33a93e46c0bf4e2e9e556db21bc71d0a139428ad89250e56fdd2c"}
```

Checksum:

```text
e3af9e2654b33a93e46c0bf4e2e9e556db21bc71d0a139428ad89250e56fdd2c  radcra-web-store-v0.5.36.zip
```

Fixture readiness result (exit 0):

```json
{"schema_version":1,"mode":"fixture","ready":true,"manual_screenshot_required":true,"checks":{"identity":true,"public_site":true,"privacy_disclosure":true,"support":true,"promo":true,"screenshot":false,"package":true,"checksum":true,"production_inputs":false},"errors":["screenshot_missing"]}
```

`production_inputs:false` is correct: the package deliberately contains example hosts and the checked-in fixture public key. It is evidence for the pipeline, not the production Store upload.

## Artwork

- Promotional tile: ready; the committed sanitised `radcra-promo-440x280.png` passes format, dimensions, metadata, and documentation checks.
- Extension icons: ready in the generated package, including the 128 px transparent-content bounds.
- Store screenshot: unavailable. A real, current RADCRA 0.5.36 product screenshot must be captured manually at exactly 1280×800, inspected and sanitised without fabricating or substituting the interface, and kept outside the extension ZIP. This is an explicit manual artwork gate.

## Public endpoints

The committed source targets these endpoints:

- <https://radicalmove.github.io/radcra/>
- <https://radicalmove.github.io/radcra/privacy/>
- <https://radicalmove.github.io/radcra/support/>
- <https://radicalmove.github.io/radcra/latest.json>

They remain external gates awaiting the GitHub repository rename to `radicalmove/radcra`, reviewed push, GitHub Pages Actions deployment, and successful unauthenticated HTTPS/schema checks. Local source validation does not prove those public endpoints are deployed.

## Exact production inputs required

The release operator must supply and verify:

- `MOODLE_HOST_PATTERNS`: approved production Moodle HTTPS match patterns;
- `OPTIONAL_FRAME_PATTERNS`: approved optional Rise/SCORM HTTPS match patterns;
- `REVIEW_SERVICE_ORIGIN`: the live public HTTPS review-service origin;
- `EXTENSION_PUBLIC_KEY`: the production RSA SPKI public key securely derived from `EXTENSION_PRIVATE_KEY_PEM`, compared with the accepted pilot identity, and distinct from development/fixture keys;
- `BUILD_COMMIT`: the full lowercase 40-character hash automatically derived from the exact reviewed/tagged commit;
- `EXTENSION_PRIVATE_KEY_PEM`: the protected CI/account secret used only in the approved release workflow and never written to the repository, extension directory, ZIP, report, logs, or Pages artifact.

## Remaining external/manual steps

1. Rename the GitHub repository to `radcra`, update the local remote, push the reviewed commit/tag, enable Pages through Actions, and verify the four public endpoints unauthenticated.
2. Configure the secure production inputs, generate the exact 0.5.36 production ZIP/checksum from the tagged commit, validate it in submission mode, load it in a clean Chrome profile, and complete the documented smoke test.
3. Capture and sanitise the genuine 1280×800 RADCRA 0.5.36 screenshot; inspect the screenshot, icon, and promotional tile at dashboard size.
4. Create/configure the Chrome Web Store developer item, private trusted-testers distribution, listing, nine Privacy selections, Remote code `No`, Limited Use certifications, support/privacy/homepage URLs, and private Test instructions.
5. Supply reviewer credentials and private test URLs only through the Store Test instructions field or another approved private channel.
6. Upload the exact production ZIP and compare its public key and resulting Store Item ID with the accepted pilot extension identity; stop on any mismatch.
7. Run the reviewer guide against the submitted package and account, choose deferred publishing, and obtain explicit release approval before publishing or inviting testers.

Until every item above succeeds, RADCRA is locally verified and submission-shaped, not actually ready for Store submission or publication.
