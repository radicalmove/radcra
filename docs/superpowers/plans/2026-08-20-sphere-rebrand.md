# Sphere Rebrand and Interface System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the course-review extension to Sphere, apply the approved CUBE-derived visual system, add author-first-name comment excerpts and a two-state chevron panel control, and ship the 0.6.0 pilot/Store release without changing review data or navigation behaviour.

**Architecture:** Keep the existing Shadow DOM overlay and comment renderer boundaries. Add a small shared Sphere token stylesheet/string used by both overlay and renderer, a display-only first-name helper, and a panel-control state synchroniser. Keep generated runtime assets separate from manually captured Store evidence. Update branding and public URLs through the existing build/release configuration while retaining the legacy RADCRA metadata endpoint for 0.5.x update discovery.

**Tech Stack:** TypeScript, Vite, native DOM/Shadow DOM, Node test runner, Python/Pillow asset generators, Python unittest/pytest release validators, GitHub Pages and GitHub Actions.

---

## File map and responsibilities

- Modify `extension/src/build-config.ts`, `extension/src/update-checker.ts`, `extension/src/content.ts`, `extension/vite.config.ts`, `extension/package.json`, `extension/package-lock.json`: Sphere product name, 0.6.0, canonical update host and policy/help URLs. Keep `extension/public/manifest.json` version `0.0.0` as the required source placeholder; only generated `extension/dist/manifest.json` becomes 0.6.0.
- Create `extension/src/ui/sphere-tokens.ts`: one source for CUBE-derived Sphere CSS custom properties and shared typography/accessibility defaults. Add the four locally packaged Poppins weights used by the UI and copy them through the existing Vite close-bundle asset plugin; do not load fonts or other assets from a remote URL.
- Modify `extension/src/overlay/root.ts` and `extension/src/overlay/styles.css`: apply Sphere tokens, remove legacy override conflict, add the two-state chevron control and synchronised panel state.
- Modify `extension/src/comment-renderer.ts`, `extension/src/anchors/pin.ts`, `extension/src/anchors/recover.ts`: apply the same token layer to inline comments, markers and selected-text highlight treatment.
- Create `extension/src/ui/comment-author.ts`: deterministic first-name extraction and visible/accessible author formatting.
- Modify `extension/src/ui/icon-family.ts`, `scripts/generate-extension-icons.py`, `scripts/generate-store-assets.py`: Sphere logo and generated asset names/content.
- Modify the actual extension test files `extension/tests/overlay.test.ts`, `extension/tests/content.test.ts`, `extension/tests/comment-renderer.test.ts`, `extension/tests/update-checker.test.ts`, `extension/tests/manifest.test.ts`, and `extension/e2e/version-layout.spec.ts`: UI, author, accessibility, URL and regression coverage.
- Modify `tests/test_store_readiness.py`, `tests/test_public_release_site.py`, `tests/test_store_package.py`, `tests/test_release_artifacts.py`: exact 0.6.0 Sphere assets, URLs, package and legacy compatibility checks.
- Modify `site/index.html`, `site/download/index.html`, `site/privacy/index.html`, `site/support/index.html`, `site/latest.json`, `.github/workflows/pages.yml`, `.github/workflows/release-extension.yml`, `README.md`, `extension/README.md`, the runtime branding/help/policy strings, `docs/*.md`, `deploy/scripts/release-pilot-extension.sh`, `deploy/scripts/store_package.py`, `deploy/scripts/store_readiness.py`: public branding, canonical Sphere links, compatibility metadata, package names and release evidence. Create `docs/release-evidence/sphere-web-store-v0.6.0.report.json` only after the clean release checks have completed.
- Create/update `store-assets/sphere-promo-440x280.png` and manually capture `store-assets/sphere-screenshot-1280x800.png`; keep both outside `extension/dist` and the runtime ZIP.

### Task 1: Lock the version, identity constants and failing tests

**Files:** `extension/package.json`, `extension/package-lock.json`, `extension/src/build-config.ts`, `extension/src/update-checker.ts`, `extension/src/content.ts`, `extension/vite.config.ts`, `extension/public/manifest.json` (placeholder only), `extension/tests/build-config.test.ts`, `extension/tests/manifest.test.ts`, `extension/tests/update-checker.test.ts`, `extension/e2e/version-layout.spec.ts`.

- [ ] Bootstrap a fresh checkout before TDD: `(cd extension && npm ci)`, `python3 -m pip install -r scripts/requirements-build.txt`, `python3 -m pip install PyYAML`, and `(cd server && python3 -m pip install -e '.[dev]')`. Confirm `node --version`, `python3 --version`, and `git status --short` before editing.
- [ ] Write failing assertions for `Sphere - Course Review App (BETA)`, version `0.6.0`, canonical `https://radicalmove.github.io/sphere/latest.json`, absence of the old RADCRA host from the generated 0.6.0 manifest, and preservation of the `0.0.0` source-manifest placeholder.
- [ ] Run `cd extension && node --test tests/build-config.test.ts tests/manifest.test.ts tests/update-checker.test.ts`; expect failures against RADCRA/0.5.38.
- [ ] Bump package and lock versions to 0.6.0 and update build constants, `update-checker.ts`, `content.ts` and `vite.config.ts` without changing the extension signing key. Leave `extension/public/manifest.json` version at `0.0.0`; build output alone receives the generated name/version/permissions.
- [ ] Add only the Sphere metadata host to the new generated manifest and preserve the legacy `/radcra/latest.json` response server-side/Pages-side, not as a new 0.6.0 runtime permission. Keep review-service and Moodle permissions unchanged.
- [ ] Run `cd extension && node --test tests/build-config.test.ts tests/manifest.test.ts tests/update-checker.test.ts && npm run typecheck`; expect PASS.
- [ ] Update the Playwright fixture's expected pilot version/build diagnostics from the old fixture value to the version-injected 0.6.0 test value, without weakening its 320 CSS-pixel/200% zoom assertions.
- [ ] Commit as `chore: start Sphere 0.6.0 identity migration`.

### Task 2: Introduce the shared Sphere token layer

**Files:** Create `extension/src/ui/sphere-tokens.ts`; add local `extension/public/fonts/Poppins-Regular.ttf`, `Poppins-Medium.ttf`, `Poppins-SemiBold.ttf`, `Poppins-Bold.ttf` and the matching licence/provenance note; modify `extension/src/overlay/root.ts`, `extension/src/overlay/styles.css`, `extension/src/comment-renderer.ts`, `extension/src/anchors/pin.ts`, `extension/src/anchors/recover.ts`, `extension/vite.config.ts`.

- [ ] Add style assertions to `extension/tests/overlay.test.ts`, `extension/tests/comment-renderer.test.ts`, `extension/tests/pin-anchor.test.ts` and `extension/tests/recovery.test.ts` that overlay, standalone SCORM renderer, pin markers, recovered selected-text highlights and dialogs contain Sphere tokens (`--sphere-*` mapped to the approved blue ramp, surfaces, semantic colours, Poppins, 4px spacing, 6px/8px radii) and no legacy teal toolbar override is active.
- [ ] Run `cd extension && node --test tests/overlay.test.ts tests/comment-renderer.test.ts tests/pin-anchor.test.ts tests/recovery.test.ts`; expect failures because current styles use hard-coded teal/red/black values.
- [ ] Implement the token string and compose it before component styles in both Shadow DOM roots. Add `@font-face` declarations for `Poppins` weights 400, 500, 600 and 700 using `chrome.runtime.getURL("fonts/Poppins-Regular.ttf")`, `chrome.runtime.getURL("fonts/Poppins-Medium.ttf")`, `chrome.runtime.getURL("fonts/Poppins-SemiBold.ttf")` and `chrome.runtime.getURL("fonts/Poppins-Bold.ttf")` with a system fallback, and test that all four URLs are present in the emitted CSS. Record the source/version/SIL OFL licence in `extension/public/fonts/README.md`. Use `#185FA5`/white for 13px primary buttons to meet WCAG 2.2 SC 1.4.3; use `#378ADD` for links, selected states and focus emphasis; reserve red for destructive/error states.
- [ ] Replace status dots with accessible state words or a semantic tint while preserving existing connection/authentication text and state transitions.
- [ ] Run `cd extension && node --test tests/overlay.test.ts tests/comment-renderer.test.ts tests/pin-anchor.test.ts tests/recovery.test.ts && npm run typecheck && npm run build`; expect PASS and verify `dist/fonts/` is present.
- [ ] Commit as `feat: add Sphere design tokens`.

### Task 3: Build and test the Sphere logo and Store assets

**Files:** `extension/src/ui/icon-family.ts`, `scripts/generate-extension-icons.py`, `scripts/generate-store-assets.py`, `store-assets/source/README.md`, `tests/test_store_readiness.py`, `tests/test_store_package.py`.

- [ ] Write tests for exact generated files `extension/public/icons/icon16.png`, `icon48.png`, `icon128.png`, `store-assets/sphere-promo-440x280.png`; assert RGBA icon sizes, 128px alpha bounding box `(16,16,112,112)`, promo RGB 440x280, deterministic bytes and committed golden hashes.
- [ ] Run `python3 -m unittest tests/test_store_readiness.py -v`; expect the new Sphere asset/name assertions to fail.
- [ ] Replace the speech-bubble generator artwork with an original geometric Sphere mark that retains a restrained comment cue, uses only the approved palette and remains legible at all three icon sizes.
- [ ] Rename generator outputs to the Sphere filenames and update provenance/source documentation. Keep generated assets deterministic and use the exact checked-in `store-assets/source/DejaVuSans-Bold.ttf` (with its pinned hash/provenance note) for promotional text; test that the generator opens that path and fails closed if it is missing or changed.
- [ ] Generate assets with `python3 scripts/generate-extension-icons.py --output-directory extension/public/icons` and `python3 scripts/generate-store-assets.py --output store-assets/sphere-promo-440x280.png`, update golden hashes, and verify generation into a temporary directory does not dirty committed files.
- [ ] Run `python3 -m unittest tests/test_store_readiness.py tests/test_store_package.py -v`; expect PASS.
- [ ] Commit as `feat: add deterministic Sphere identity assets`.

### Task 4: Add author-first-name rendering

**Files:** Create `extension/src/ui/comment-author.ts`; modify `extension/src/overlay/root.ts` and `extension/src/comment-renderer.ts`; update `extension/tests/comment-renderer.test.ts` and `extension/tests/overlay.test.ts`.

- [ ] Write tests for `trim -> split on whitespace -> first token`, punctuation/extra-space handling, malformed/missing display-name fallback, and an accessible label that retains the full available display name.
- [ ] Run `cd extension && node --test tests/comment-renderer.test.ts tests/overlay.test.ts`; expect FAIL because no helper exists.
- [ ] Implement a display-only helper. Do not loosen API validation of `author.display_name`; the missing-name case is defensive rendering/test coverage only.
- [ ] Render every comment excerpt as a first-name span in secondary Sphere blue followed by the quoted comment body in deep navy. Apply it to whole-course/current-page/open/resolved/grouped lists and preserve existing truncation, order, navigation and keyboard behaviour.
- [ ] Run `cd extension && node --test tests/comment-renderer.test.ts tests/overlay.test.ts tests/content.test.ts && npm run typecheck`; expect PASS. Assert the accessible label contains both the full available display name and the complete comment excerpt, even though the visible list uses only the first name.
- [ ] Commit as `feat: show comment authors in Sphere lists`.

### Task 5: Add the two-state chevron minimise control

**Files:** `extension/src/overlay/root.ts`, `extension/src/overlay/styles.css`, `extension/src/ui/icon-family.ts`, `extension/tests/overlay.test.ts`, `extension/tests/panel-state.test.ts`, `extension/tests/icon-family.test.ts`.

- [ ] Write tests for open state (`chevron-down`, `Minimise comments`, `aria-expanded=true`) and closed state (`chevron-up`, `Expand comments`, `aria-expanded=false`), shared `aria-controls`, keyboard activation, focus retention, narrow width and 200% zoom-safe layout.
- [ ] Run `cd extension && node --test tests/overlay.test.ts tests/panel-state.test.ts`; expect FAIL because only the Comments control exists.
- [ ] Add the icon-only button to the top-right of the toolbar and route it and the Comments button through one panel-toggle function. Update icon, native `title` and accessible name from the same state source.
- [ ] Ensure the control has a 32px minimum target and cannot overlap the title/version/Comments/Help controls at the supported narrow layout.
- [ ] Add an icon-control audit covering marker/highlight controls, group toggles, chevrons, save/edit/delete/help and the new minimise control: every icon-only control must have both a native `title` and a non-empty accessible name.
- [ ] Run `cd extension && node --test tests/overlay.test.ts tests/panel-state.test.ts && npx playwright test e2e/version-layout.spec.ts && npm test`; expect PASS, including the existing 320 CSS-pixel/200% zoom layout coverage updated for 0.6.0.
- [ ] Commit as `feat: add Sphere panel minimise control`.

### Task 6: Complete public Sphere migration and compatibility URLs

**Files:** `site/index.html`, `site/download/index.html`, `site/privacy/index.html`, `site/support/index.html`, `site/latest.json`, new `site/legacy/radcra/index.html`, `site/legacy/radcra/privacy/index.html`, `site/legacy/radcra/support/index.html`, `site/legacy/radcra/latest.json`, `.github/workflows/pages.yml`, `docs/chrome-web-store-listing.md`, `docs/privacy-policy.md`, `docs/chrome-web-store-reviewer-guide.md`, `docs/chrome-web-store-pre-submission-checklist.md`, `docs/releasing.md`, `store-assets/README.md`, `README.md`, `extension/README.md`, `tests/test_public_release_site.py`.

- [ ] Add failing public-site assertions for Sphere branding, exact canonical `https://radicalmove.github.io/sphere/` links, 0.6.0 package names, complete privacy/support copy, one beta warning per public page, and a legacy `/radcra/latest.json` compatibility entry. Add a Pages deployment test asserting the staging tree contains both `sphere/` and `radcra/latest.json`.
- [ ] Provision the one-time `radicalmove/radicalmove.github.io` user-site repository (or confirm the existing equivalent) and a narrowly scoped `SPHERE_PAGES_REPOSITORY_TOKEN` Actions secret. The Pages workflow publishes the current `site/` under `sphere/` and compatibility-only `radcra/index.html`, `radcra/privacy/index.html`, `radcra/support/index.html` and `radcra/latest.json` under that user-site root; legacy pages contain only a Sphere migration link/metadata and no course, review, credential, token or executable content.
- [ ] Update `.github/workflows/pages.yml` to build and publish that two-path Pages artifact. The workflow must set `set +x`, require `SPHERE_PAGES_REPOSITORY_TOKEN`, clone with `git -c "http.extraheader=AUTHORIZATION: bearer ${SPHERE_PAGES_REPOSITORY_TOKEN}" clone --branch main --depth 1 https://github.com/radicalmove/radicalmove.github.io.git "$RUNNER_TEMP/sphere-pages"`, replace only `$RUNNER_TEMP/sphere-pages/sphere/` and `$RUNNER_TEMP/sphere-pages/radcra/`, copy committed `site/` into `sphere/`, copy `site/legacy/radcra/index.html`, `privacy/index.html`, `support/index.html` and `latest.json` into `radcra/`, then commit and push those paths to `main` with the workflow bot identity using the same masked `http.extraheader`. Source `sphere/` from the committed `site/` directory, source the four legacy paths from committed templates/fixture, and fail if the token or destination repository is unavailable. Run the public-site smoke test against exactly six unauthenticated URLs: `https://radicalmove.github.io/sphere/`, `/sphere/download/`, `/sphere/privacy/`, `/sphere/support/`, `/sphere/latest.json`, and `/radcra/latest.json`, plus a migration-page assertion for `/radcra/`. Assert the six URL/page contracts and that `/sphere/download/` is the canonical download surface.
- [ ] Update user-facing copy, download links, privacy/support links, release metadata, Store instructions and artwork names to Sphere. Keep the legacy metadata endpoint as a minimal static compatibility response that points to the canonical Sphere release page and contains no course/review data.
- [ ] Run an inventory scan (`rg -n "RADCRA|radcra|Beta-testing-app" README.md extension site docs scripts deploy .github`) and classify only historical design specs, immutable historical release reports, and the legacy compatibility tree/endpoint as allowed exceptions. Update runtime help/policy strings, background diagnostics, `README.md`, `extension/README.md`, pilot test instructions and current Store/reviewer documents; preserve old report filenames intentionally so immutable evidence remains verifiable.
- [ ] Update the Store/reviewer docs to describe the Sphere name, author-prefixed comments, chevron states, new assets and exact canonical/legacy update behaviour.
- [ ] Run `python3 -m pytest -q tests/test_public_release_site.py tests/test_store_readiness.py`; expect PASS.
- [ ] Commit as `docs: publish Sphere release surfaces`.

### Task 7: Update packaging and release automation

**Files:** `deploy/scripts/release-pilot-extension.sh`, `deploy/scripts/release_artifacts.py`, `deploy/scripts/store_package.py`, `deploy/scripts/store_readiness.py`, `.github/workflows/release-extension.yml`, `tests/test_deployment_package.py`, `tests/test_store_package.py`, `tests/test_release_artifacts.py`, `tests/test_store_readiness.py`, `extension/tests/icon-family.test.ts`, `extension/tests/background.test.ts`.

- [ ] Write failing assertions for Sphere package/report names, canonical repository/download URLs, 0.6.0 version, Sphere icon/font names and exact runtime package membership. Keep the Web Store ZIP boundary explicit (manifest, background, content, icons and the four packaged Poppins weights); keep the nested pilot archive's `RELEASE.json`/directory structure separate and unchanged except for Sphere names. Extend the pilot artifact file list and its tests to include `fonts/Poppins-*.ttf` in both the unpacked pilot directory and nested pilot ZIP.
- [ ] Update scripts/workflow paths, report keys, checksum names, Store package names and readiness expectations. Keep promotional art and the manual screenshot outside runtime ZIPs. Do not put private key material in artifacts or logs. Keep the technical GitHub repository identifier `radicalmove/radcra` only in non-user-facing immutable report/evidence fields needed for historical verification; every public `release_url`, download link, HTML link and Store/reviewer URL must use `https://radicalmove.github.io/sphere/` (or its `/sphere/...` child). Add tests that reject `radicalmove/radcra` from public links while allowing it only in explicitly marked technical fields.
- [ ] Add explicit checks that package/report/runtime diagnostics contain Sphere canonical URLs and the exact 40-character build commit, that the compatibility metadata is present, and that the Web Store ZIP contains exactly the documented runtime files plus the four local Poppins font files while the nested pilot package retains its separate `RELEASE.json` layout.
- [ ] Run `python3 -m unittest tests/test_store_package.py tests/test_deployment_package.py tests/test_store_readiness.py tests/test_release_artifacts.py`; expect PASS.
- [ ] Commit as `build: prepare Sphere 0.6.0 release pipeline`.

### Task 8: Capture genuine screenshot and run complete verification

**Files:** `store-assets/sphere-screenshot-1280x800.png`, readiness report and generated release evidence.

- [ ] Build a clean 0.6.0 preview with the existing production signing key and exact build commit; load `extension/dist` in Chrome.
- [ ] Capture a genuine 1280x800 Chrome screenshot showing Sphere, the author-prefixed comment list, the chevron control and contextual comment content. Sanitize credentials, email addresses, tokens, student data, invitations and private URLs; do not fabricate the UI. Commit this screenshot before generating release artifacts so the release script runs from a clean worktree.
- [ ] Manually record pass evidence for these real-browser scenarios: (a) ordinary Moodle page, open a comment, see the first name and full quoted body; (b) minimise/reopen with both toolbar controls and keyboard; (c) create a text-highlight and area marker; (d) navigate to a comment in a Rise tabs interaction; (e) navigate to a comment in a Rise process step; (f) reload and repeat (d)/(e); and (g) sign out/reconnect. Repeat (a)-(g) on at least one SCORM/Rise page and one ordinary Moodle page before accepting the screenshot.
- [ ] Verify screenshot dimensions, PNG format, metadata hygiene and manual-capture requirements; keep it outside `extension/dist` and the runtime ZIP.
- [ ] Produce local release artifacts only after the screenshot commit, using one explicit shell block so its external root persists for both packaging and readiness: `export PRIVATE_KEY_PATH="${PRIVATE_KEY_PATH:?Set PRIVATE_KEY_PATH to the real production PEM path}"; export REVIEW_SERVICE_ORIGIN="${REVIEW_SERVICE_ORIGIN:?Set REVIEW_SERVICE_ORIGIN to the real production HTTPS origin}"; export OPTIONAL_FRAME_PATTERNS="$(awk 'NF && $1 !~ /^#/ { printf "%s%s", separator, $0; separator="," }' deploy/config/pilot-optional-frame-patterns.txt)"; export BUILD_COMMIT="$(git rev-parse HEAD)"; export SPHERE_ARTIFACT_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/sphere-release-assets.XXXXXX")"; trap 'rm -rf "$SPHERE_ARTIFACT_ROOT"' EXIT; PRIVATE_KEY_PATH="$PRIVATE_KEY_PATH" REVIEW_SERVICE_ORIGIN="$REVIEW_SERVICE_ORIGIN" OPTIONAL_FRAME_PATTERNS="$OPTIONAL_FRAME_PATTERNS" BUILD_COMMIT="$BUILD_COMMIT" DELIVERY_ROOT="$SPHERE_ARTIFACT_ROOT" deploy/scripts/release-pilot-extension.sh`. The script must write the exact `sphere-web-store-v0.6.0.report.json`, `sphere-web-store-v0.6.0.zip`, and `.sha256` under that external root; use those same explicit paths for readiness before the trap removes the root. The operator must provide the real PEM path and production origin; no placeholder values may be used in a release run.
- [ ] Run the complete gates from the repository root:
  - `(cd extension && npm test && npm run typecheck && npm run build)`
  - `(cd server && python3 -m pytest -q)`
  - `python3 -m unittest tests/test_deployment_package.py tests/test_store_package.py tests/test_store_readiness.py tests/test_public_release_site.py tests/test_release_artifacts.py`
  - `git diff --check`
- [ ] Run the production Store-readiness validator inside that same shell block in `submission` mode against the explicit external paths: `python3 deploy/scripts/store_readiness.py --mode submission --root "$PWD" --package-report "$SPHERE_ARTIFACT_ROOT/sphere-web-store-v0.6.0.report.json" --checksum "$SPHERE_ARTIFACT_ROOT/sphere-web-store-v0.6.0.zip.sha256" --screenshot "$PWD/store-assets/sphere-screenshot-1280x800.png"`; expect `ready: true` and no errors. Before the cleanup trap runs, execute `mkdir -p docs/release-evidence && cp "$SPHERE_ARTIFACT_ROOT/sphere-web-store-v0.6.0.report.json" docs/release-evidence/sphere-web-store-v0.6.0.report.json && cp "$SPHERE_ARTIFACT_ROOT/sphere-web-store-v0.6.0.zip.sha256" docs/release-evidence/sphere-web-store-v0.6.0.zip.sha256`, then remove the temporary root.
- [ ] Commit the genuine screenshot once before artifact generation, and commit the copied readiness evidence afterward as `docs: capture Sphere 0.6.0 Store evidence`; do not claim that deleted temporary artifacts were committed.

### Task 9: Publish the immutable 0.6.0 release

**Files:** release artifacts under the configured delivery root; Git tag `v0.6.0`.

- [ ] Run the existing release script from the clean final commit with the operator-supplied production private key path, `REVIEW_SERVICE_ORIGIN`, optional frame patterns from `deploy/config/pilot-optional-frame-patterns.txt`, and `BUILD_COMMIT` set to the final lowercase 40-character commit. First update the script contract so it accepts/validates the supplied `BUILD_COMMIT` and does not silently replace it with a different HEAD value; require it to equal `git rev-parse HEAD`.
- [ ] Verify the pilot ZIP, Web Store ZIP, per-archive checksums, `SHA256SUMS`, release notes, readiness report and package report all identify Sphere 0.6.0 and contain no unexpected runtime files.
- [ ] Create and push annotated tag `v0.6.0`; do not rewrite an existing immutable tag.
- [ ] Monitor the GitHub Actions release workflow through its full test, build, readiness and publish stages. If any gate fails, keep the tag immutable and fix forward with the next version.
- [ ] Confirm canonical Sphere Pages URLs and the legacy RADCRA metadata URL are reachable over unauthenticated HTTPS, then report the release locations and final verification counts.
