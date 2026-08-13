# RADCRA Chrome Web Store Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare RADCRA 0.5.35 for a private Chrome Web Store beta while adding a verified GitHub download/update path and preserving course-review behavior.

**Architecture:** Keep review behavior and the existing pilot release pipeline intact. Add a trusted background privacy-consent gate, a read-only release-metadata checker, a separate root-level Web Store package, and a GitHub Pages/release workflow. The existing nested unpacked pilot ZIP remains a distinct artifact.

**Tech Stack:** TypeScript, Node’s built-in test runner, Vite/esbuild, Python 3 standard library, Pillow for deterministic icon generation, GitHub Actions/Pages, Chrome Manifest V3.

---

## File map

- `extension/src/policy-consent.ts`: versioned local acknowledgement state, invalidation, and access-state clearing helpers.
- `extension/src/update-checker.ts`: strict latest-metadata schema, SemVer comparison, 24-hour cache policy, and safe fetch result.
- `extension/src/background.ts`: policy gate for all network/data routes and update-check message handling.
- `extension/src/content.ts`, `extension/src/overlay/root.ts`, `extension/src/overlay/styles.css`: first-run disclosure, acknowledgement callback, and Help update status/action.
- `extension/src/build-config.ts`, `extension/vite.config.ts`, `extension/public/manifest.json`: update endpoint host permission, beta identity, and icon manifest generation.
- `extension/public/icons/*.png`, `scripts/generate-extension-icons.py`, `scripts/requirements-build.txt`: deterministic store icons and pinned Pillow build dependency.
- `extension/tests/policy-consent.test.ts`, `extension/tests/update-checker.test.ts`, `extension/tests/background.test.ts`, `extension/tests/overlay.test.ts`, `extension/tests/build-config.test.ts`, `extension/tests/manifest.test.ts`: test-first coverage.
- `deploy/scripts/store_package.py`: root-level deterministic Web Store ZIP and package validator.
- `deploy/scripts/release_artifacts.py`, `deploy/scripts/release-pilot-extension.sh`, `tests/test_deployment_package.py`: preserve and extend unpacked release artifacts/checksums/icons.
- `tests/test_store_package.py`: validator/package tests.
- `docs/privacy-policy.md`, `site/privacy/index.html`, `site/download/index.html`, `site/latest.json`: public policy, download instructions, and metadata endpoint.
- `docs/chrome-web-store-listing.md`, `docs/chrome-web-store-reviewer-guide.md`, `docs/releasing.md`, `extension/README.md`: store submission, reviewer access, update, and pilot instructions.
- `.github/workflows/pages.yml`, `.github/workflows/release-extension.yml`: Pages deployment and tagged release publishing.
- `extension/package.json`, `extension/package-lock.json`: canonical version 0.5.35.

### Task 1: Add deterministic store identity and icon assets

**Files:**
- Modify: `extension/package.json`, `extension/package-lock.json`, `extension/public/manifest.json`, `extension/src/build-config.ts`, `extension/vite.config.ts`
- Create: `scripts/generate-extension-icons.py`, `extension/public/icons/icon16.png`, `extension/public/icons/icon48.png`, `extension/public/icons/icon128.png`
- Create: `scripts/requirements-build.txt`
- Test: `extension/tests/build-config.test.ts`, `extension/tests/manifest.test.ts`

- [ ] **Step 1: Write failing identity/icon tests.** Assert package/lock version `0.5.35`, generated manifest name `RADCRA — Course Review (BETA)`, exact beta description containing `THIS EXTENSION IS FOR BETA TESTING`, icon paths/sizes, generated `dist/icons/icon16.png`, `icon48.png`, and `icon128.png`, and the fixed update host permission.
- [ ] **Step 2: Run focused tests to verify failure.** Run `node --test --test-concurrency=1 tests/build-config.test.ts tests/manifest.test.ts`; expect failures for the old version/name, missing icons, and missing update host.
- [ ] **Step 3: Implement the minimum build/config changes.** Add the canonical version, beta identity, fixed `https://radicalmove.github.io/Beta-testing-app/*` host, and generated manifest icon references. Add an explicit Vite copy plugin/close-bundle step because `publicDir: false` is intentional; it must copy the three PNGs from `public/icons/` to `dist/icons/`. Keep the public manifest version at `0.0.0` and keep the accepted public key unchanged.
- [ ] **Step 4: Pin and generate icons.** Add a pinned Pillow version to `scripts/requirements-build.txt`. Implement `scripts/generate-extension-icons.py` with Pillow to draw one consistent teal comment-marker mark and write exact 16x16, 48x48, and 128x128 PNGs. Make the script deterministic and fail if dimensions or alpha mode are wrong.
- [ ] **Step 5: Run focused tests and build.** Run `node --test --test-concurrency=1 tests/build-config.test.ts tests/manifest.test.ts` and `npm run build`; expect all focused tests to pass and `dist/manifest.json` plus `dist/icons/` to contain the generated identity/assets.
- [ ] **Step 6: Commit.** `git add extension/package.json extension/package-lock.json extension/public extension/src/build-config.ts extension/vite.config.ts scripts/generate-extension-icons.py scripts/requirements-build.txt extension/tests && git commit -m "feat: prepare RADCRA beta store identity"`.

### Task 2: Implement the versioned privacy acknowledgement and background gate

**Files:**
- Create: `extension/src/policy-consent.ts`, `extension/tests/policy-consent.test.ts`
- Modify: `extension/src/background.ts`, `extension/src/background-bridge.ts`, `extension/src/content.ts`, `extension/tests/background.test.ts`, `extension/tests/background-bridge.test.ts`

- [ ] **Step 1: Write failing consent-state tests.** Cover absent/malformed state, current-version acknowledgement, invalidation after a policy-version change, safe storage errors, and clearing session/device/reviewer keys when invalidated.
- [ ] **Step 2: Run the consent tests to verify failure.** Run `node --test --test-concurrency=1 tests/policy-consent.test.ts`; expect missing-module/function failures.
- [ ] **Step 3: Implement the storage-only consent module.** Define `POLICY_VERSION`, exact storage key/schema, `readPolicyState`, `acknowledgePolicy`, `requiresPolicyAcknowledgement`, and `clearAccessState`. Treat malformed/unavailable storage as not acknowledged; never include credentials in the acknowledgement record.
- [ ] **Step 4: Add failing background-gate tests.** Assert a fresh or invalidated install rejects `AUTHENTICATE`, course lookup/resolve, viewer/comment/list/mutation/upload routes, SCORM launch registration, and automatic device/token renewal before any fetch; assert acknowledgement permits them; assert frame coordination remains local and does not call the API.
- [ ] **Step 5: Run the gate tests to verify failure.** Run `node --test --test-concurrency=1 tests/background.test.ts tests/background-bridge.test.ts`; expect the new no-network assertions to fail.
- [ ] **Step 6: Gate all trusted network/data routes.** In `background.ts`, load the consent store before startup renewal and before route operations. Add exact `GET_POLICY_STATUS` and `ACK_POLICY` messages that do not make network requests. On invalidation, clear active session/device credentials before returning `policy-required`. Apply the gate before API client creation, course lookup, authentication, course resolve/register, comment/list/viewer/mutation/upload, and SCORM registration paths that carry review context. Preserve existing sender/course authorization after the gate.
- [ ] **Step 7: Run the focused gate tests.** Run `node --test --test-concurrency=1 tests/policy-consent.test.ts tests/background.test.ts tests/background-bridge.test.ts`; expect all to pass.
- [ ] **Step 8: Commit.** `git add extension/src/policy-consent.ts extension/src/background.ts extension/src/background-bridge.ts extension/src/content.ts extension/tests && git commit -m "feat: gate review data behind privacy acknowledgement"`.

### Task 3: Add the first-run disclosure and policy migration UX

**Files:**
- Modify: `extension/src/content.ts`, `extension/src/overlay/root.ts`, `extension/src/overlay/styles.css`, `extension/tests/overlay.test.ts`, `extension/tests/content.test.ts`
- Create: `docs/privacy-policy.md`, `site/privacy/index.html`

- [ ] **Step 1: Write failing UI tests.** Assert a fresh install shows a prominent disclosure before sign-in/course resolution, includes the data summary, Limited Use wording, exact public policy URL, Continue/Decline controls, and does not submit a network-bearing message until Continue. Assert a policy-version change returns to the disclosure and signed-out state.
- [ ] **Step 2: Run focused UI tests to verify failure.** Run `node --test --test-concurrency=1 tests/overlay.test.ts tests/content.test.ts`; expect missing disclosure/gating failures.
- [ ] **Step 3: Add the public policy content.** Write `docs/privacy-policy.md` and the matching static HTML at `/privacy/`, covering reviewer identity/email, authentication/session material, course/page URLs/titles, selected text, comments/replies/status, screenshots, logs, purpose, sharing, retention/deletion, HTTPS, token boundaries, support URL, and the literal Chrome Limited Use statement.
- [ ] **Step 4: Implement disclosure rendering and acknowledgement.** Add a modal/banner in the overlay with keyboard focus, explicit Continue/Decline, accessible live/error states, policy link, and a policy-version label. On Continue send `ACK_POLICY`, then resume the existing course-access flow; on Decline remain signed out and do not retry network calls. On `policy-required` responses, clear stale connected UI and show the same disclosure.
- [ ] **Step 5: Keep content startup network-free until acknowledgement.** Change `startCourseReview` to request only policy status first. Do not call `RESOLVE_COURSE`, lookup, viewer, comments, or renewal until the background reports acknowledged. Preserve normal existing flow after acknowledgement.
- [ ] **Step 6: Run focused UI tests.** Run `node --test --test-concurrency=1 tests/overlay.test.ts tests/content.test.ts`; expect all new and existing tests to pass.
- [ ] **Step 7: Commit.** `git add extension/src/content.ts extension/src/overlay extension/tests docs/privacy-policy.md site/privacy/index.html && git commit -m "feat: add Chrome data-use disclosure"`.

### Task 4: Implement the safe GitHub release metadata checker

**Files:**
- Create: `extension/src/update-checker.ts`, `extension/tests/update-checker.test.ts`
- Modify: `extension/src/background.ts`, `extension/src/content.ts`, `extension/src/overlay/root.ts`, `extension/tests/background.test.ts`, `extension/tests/overlay.test.ts`

- [ ] **Step 1: Write failing metadata/cache tests.** Cover exact schema parsing, HTTPS URL restrictions, SemVer comparison, downgrade/no-update cases, malformed JSON, 24-hour cache suppression, retry after failure, and no remote-code execution.
- [ ] **Step 2: Run focused tests to verify failure.** Run `node --test --test-concurrency=1 tests/update-checker.test.ts`; expect missing-module/function failures.
- [ ] **Step 3: Implement strict checker primitives.** Add the fixed endpoint, `UpdateMetadata` schema, SemVer comparator, cache schema, `shouldCheck`, and a fetcher that only parses JSON data and returns safe status values. Cache successful and failed checks with timestamps without storing course/user data.
- [ ] **Step 4: Add background message tests.** Assert `CHECK_FOR_UPDATE` is authorized, uses the exact endpoint, performs at most one fetch per 24 hours, and returns a release URL/download URL without attempting to fetch or execute assets.
- [ ] **Step 5: Implement background/content/Help integration.** Add `CHECK_FOR_UPDATE` handling in the worker and a content callback passed to the overlay. Add a Help action showing “up to date”, “update available”, or retryable failure; link to the GitHub download page. Explain that unpacked builds require manual folder replacement/reload and Web Store builds update through Chrome.
- [ ] **Step 6: Run focused tests.** Run `node --test --test-concurrency=1 tests/update-checker.test.ts tests/background.test.ts tests/overlay.test.ts` and `npm run typecheck`.
- [ ] **Step 7: Commit.** `git add extension/src/update-checker.ts extension/src/background.ts extension/src/content.ts extension/src/overlay extension/tests && git commit -m "feat: add safe GitHub update checks"`.

### Task 5: Add deterministic Web Store packaging and extend pilot artifacts

**Files:**
- Create: `deploy/scripts/store_package.py`, `tests/test_store_package.py`
- Modify: `deploy/scripts/release_artifacts.py`, `deploy/scripts/release-pilot-extension.sh`, `tests/test_deployment_package.py`, `extension/README.md`

- [ ] **Step 1: Write failing package tests.** Assert a root-level Web Store ZIP, required icons/manifest, no private key/source maps/placeholder hosts/remote executable strings, deterministic ordering/timestamps, and clear rejection messages. Add compatibility tests proving legacy immutable releases still validate using their old file set.
- [ ] **Step 2: Run package tests to verify failure.** Run `python3 -m unittest tests/test_store_package.py tests/test_deployment_package.py`; expect missing script/asset failures.
- [ ] **Step 3: Implement `store_package.py`.** Accept `--dist`, `--output`, `--version`, and `--repository`; validate generated production manifest and all package files; write a root-level deterministic ZIP and a report. Include all generated extension files while excluding source maps and release metadata.
- [ ] **Step 4: Extend pilot packaging without breaking old releases.** Add icons to the current release file set and artifact comparisons/checksums. Keep separate legacy/current tuples in `release_artifacts.py` so existing 0.5.30–0.5.34 immutable releases remain verifiable. Update `release-pilot-extension.sh` to require/copy/compare icons and produce the separate Web Store ZIP beside the existing pilot ZIP.
- [ ] **Step 5: Run package tests and local production fixture.** Run `python3 -m unittest tests/test_store_package.py tests/test_deployment_package.py`, then build a production fixture and validate both ZIPs, root layout, checksums, and manifest identity.
- [ ] **Step 6: Update pilot instructions.** Document the two package types, manual unpacked reload, Web Store private-beta install, stable ID/public-key sequence, and no-private-key rule in `extension/README.md`.
- [ ] **Step 7: Commit.** `git add deploy/scripts tests extension/README.md && git commit -m "feat: package RADCRA for Web Store and pilot delivery"`.

### Task 6: Add GitHub Pages/download site and release workflows

**Files:**
- Create: `site/download/index.html`, `site/latest.json`, `.github/workflows/pages.yml`, `.github/workflows/release-extension.yml`, `docs/chrome-web-store-listing.md`, `docs/chrome-web-store-reviewer-guide.md`
- Create: `docs/releasing.md`
- Modify: `README.md`
- Test: `tests/test_public_release_site.py`

- [ ] **Step 1: Write failing site/workflow tests.** Assert exact unauthenticated URLs, download links, privacy/support links, beta listing text, valid `latest.json` schema, Pages workflow permissions/actions, and release workflow triggers/secrets/temporary-key cleanup.
- [ ] **Step 2: Run site tests to verify failure.** Run `python3 -m unittest tests/test_public_release_site.py`; expect missing files/URLs/workflow assertions.
- [ ] **Step 3: Implement the public site.** Add a responsive download page at `https://radicalmove.github.io/Beta-testing-app/`, link exact pilot/Web Store instructions and GitHub Releases, add the static policy page, and add a valid 0.5.35 `site/latest.json` placeholder with the fixed schema.
- [ ] **Step 4: Implement Pages deployment.** Add `pages.yml` for pushes to `main` affecting `site/**` and manual dispatch, using GitHub Pages artifact/deploy actions and required `pages: write`/`id-token: write` permissions.
- [ ] **Step 5: Implement tagged release workflow.** Add `release-extension.yml` on `v*.*.*` tags with exact `EXTENSION_PRIVATE_KEY_PEM` secret and `REVIEW_SERVICE_ORIGIN` variable, secure 600-mode temp PEM/trap cleanup, `github.sha` build commit, and explicit dependency/gate setup before publication: run `python3 -m pip install -r scripts/requirements-build.txt` from the repository root, `python3 -m pip install -e '.[dev]'` with `working-directory: server/`, and `python3 -m pip install PyYAML` for root deployment tests; then run `npm ci`, `npm test`, `npm run typecheck`, and `npm run build` with `working-directory: extension/`, `python3 -m pytest -q` with `working-directory: server/`, and `python3 -m unittest tests/test_deployment_package.py tests/test_store_package.py tests/test_public_release_site.py` from the repository root. It then creates both package variants, checksums, and GitHub Release assets. In the same workflow, generate `site/latest.json` and publish it to the live Pages site by uploading a Pages artifact containing the complete `site/` directory and running `actions/deploy-pages@v4` with `pages: write`/`id-token: write`; the tag deployment is the authoritative metadata update and must not commit generated files or secrets. Ensure no secrets are echoed or uploaded.
- [ ] **Step 6: Write listing/reviewer/release docs.** Create `docs/releasing.md` and include exact store title, `THIS EXTENSION IS FOR BETA TESTING`, privacy/support URLs, permission justifications, private trusted-tester setup, test credentials as out-of-repo inputs, Web Store identity/redirect procedure, GitHub Pages/release process, and post-publication update acceptance.
- [ ] **Step 7: Run site/workflow tests.** Run `python3 -m unittest tests/test_public_release_site.py` and inspect workflow YAML with a parser/linter available in the repository. Assert the release workflow includes `actions/deploy-pages@v4`, the generated version in `latest.json`, and the four exact public URLs.
- [ ] **Step 8: Commit.** `git add site .github docs README.md tests/test_public_release_site.py && git commit -m "feat: add RADCRA public download and release automation"`.

### Task 7: Produce and verify release 0.5.35

**Files:**
- Modify: `docs/pilot-test-script.md`, release metadata generated outside the repository

- [ ] **Step 1: Update release references.** Replace stale “latest version” instructions only where they describe the current release process; retain historical test reports unchanged.
- [ ] **Step 2: Run the full verification gate.** From `extension/`, run `npm test` and `npm run typecheck`; run `npm run build`; from the repository run `python3 -m unittest tests/test_deployment_package.py tests/test_store_package.py tests/test_public_release_site.py`; run `git diff --check`.
- [ ] **Step 3: Build the local production release.** With `PRIVATE_KEY_PATH` outside the repository, `REVIEW_SERVICE_ORIGIN` set, and the reviewed optional-frame patterns, run `deploy/scripts/release-pilot-extension.sh`; confirm the external `Beta Testing App-pilot-builds/releases/` folder contains the verified unpacked build, versioned/stable pilot ZIPs, root-level Web Store ZIP, checksums, and immutable metadata.
- [ ] **Step 4: Verify release identity and package contents.** Compare generated manifest version/key/name/icons, validate both ZIP layouts, run SHA256 verification, and ensure no private key or source map entered any artifact.
- [ ] **Step 5: Commit release preparation.** `git add docs/pilot-test-script.md && git commit -m "release: prepare RADCRA Chrome Web Store beta 0.5.35"`.
- [ ] **Step 6: Tag and publish only with explicit release authorization.** `git tag -a v0.5.35 -m "RADCRA 0.5.35"` and push the branch/tag only after confirming the production secret/variable setup. Do not publish the Web Store item automatically from this local task.
- [ ] **Step 7: Complete post-publication manual acceptance.** In the Chrome Developer Dashboard, upload the root-level Web Store ZIP as a private beta, verify the dashboard Item ID equals the accepted unpacked ID, configure trusted testers/privacy URL/support URL, provide reviewer access, and later confirm a higher version is offered as a browser-managed update.

## Verification summary

Before declaring the work ready, the implementation must show:

- all existing tests still pass with only documented skips;
- policy gating blocks every network-bearing review path before acknowledgement;
- update checking reads only strict JSON metadata and is rate-limited;
- the Web Store ZIP is root-level and icon-complete while pilot artifacts preserve their established layout;
- public Pages URLs and `latest.json` validate without authentication;
- release artifacts are checksum-verified and contain no secrets.
