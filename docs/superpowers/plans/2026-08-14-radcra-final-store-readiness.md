# RADCRA Final Chrome Web Store Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a locally verified RADCRA 0.5.36 private-beta submission workspace whose identity, public disclosures, permissions, artwork, package pipeline, and operator instructions align with current Chrome Web Store requirements.

**Architecture:** Keep the extension's existing fail-closed consent and review behaviour unchanged. Update one canonical lowercase `radcra` URL family across runtime metadata, public pages, workflows, tests, and Store copy; add a public support page and exact privacy declarations; generate deterministic compliant artwork; and add a separate release-workspace validator with fixture and submission modes. Account mutations and the real production package remain operator gates.

**Tech Stack:** TypeScript/Manifest V3/Vite, Node test runner, Python 3/unittest/Pillow, static HTML/JSON, GitHub Actions YAML, Chrome browser capture.

---

## File map

- `extension/src/build-config.ts`: canonical Store name, beta description, and fixed update-host permission.
- `extension/src/update-checker.ts`: exact lowercase metadata endpoint and strict metadata validation.
- `extension/src/content.ts`, `extension/src/overlay/root.ts`: exact public policy URL shown in the in-product disclosure.
- `extension/public/manifest.json`: Store-facing name/description source and runtime permissions.
- `extension/package.json`, `extension/package-lock.json`, `site/latest.json`: canonical 0.5.36 release version.
- `extension/tests/build-config.test.ts`, `extension/tests/manifest.test.ts`, `extension/tests/update-checker.test.ts`, `extension/tests/overlay.test.ts`, `extension/tests/content.test.ts`: runtime identity, endpoint, and disclosure regressions.
- `docs/privacy-policy.md`, `docs/chrome-web-store-listing.md`, `docs/chrome-web-store-reviewer-guide.md`, `docs/releasing.md`, `README.md`: authoritative public/submission guidance.
- `site/index.html`, `site/download/index.html`, `site/privacy/index.html`: public homepage/download/privacy sources.
- `site/support/index.html`: new public support page with safe reporting guidance.
- `site/latest.json`: exact five-key metadata fixture whose `download_url` points to the public homepage, not executable code or an automatically fetched archive.
- `tests/test_public_release_site.py`: exact public URL/contact/schema/workflow assertions and stale-identifier rejection.
- `scripts/generate-extension-icons.py`: deterministic Google-padded runtime icons.
- `scripts/generate-store-assets.py`: deterministic 440x280 promotional tile generated from the existing RADCRA visual identity.
- `store-assets/source/`: maintainable source notes/assets for Store artwork.
- `store-assets/radcra-promo-440x280.png`: required small promotional tile.
- `store-assets/radcra-screenshot-1280x800.png`: sanitised actual-product screenshot when the authorised browser session is available.
- `store-assets/README.md`: artwork provenance, sanitisation, and upload instructions.
- `deploy/scripts/store_readiness.py`: separate fixture/submission readiness validator; never searches for private keys.
- `tests/test_store_readiness.py`: validator modes, image dimensions/padding, stale values, and production-input report tests.
- `deploy/scripts/store_package.py`, `tests/test_store_package.py`: exact lowercase repository identity and unchanged runtime-only ZIP boundary.
- `.github/workflows/pages.yml`, `.github/workflows/release-extension.yml`: lowercase repository URLs, current validators, and Store assets in release evidence without placing listing artwork inside the extension ZIP.
- `docs/chrome-web-store-pre-submission-checklist.md`: exact external account steps and dashboard mapping.

### Task 1: Canonical product identity, URL family, and version

**Files:**
- Modify: `extension/src/build-config.ts`
- Modify: `extension/src/update-checker.ts`
- Modify: `extension/src/content.ts`
- Modify: `extension/src/overlay/root.ts`
- Modify: `extension/public/manifest.json`
- Modify: `extension/package.json`
- Modify: `extension/package-lock.json`
- Modify: `extension/tests/build-config.test.ts`
- Modify: `extension/tests/manifest.test.ts`
- Modify: `extension/tests/update-checker.test.ts`
- Modify: `extension/tests/overlay.test.ts`
- Modify: `extension/tests/content.test.ts`

- [ ] **Step 1: Write failing identity and endpoint tests.** Assert canonical version `0.5.36`, exact visible name `RADCRA - Course Review App (BETA)`, exact update permission `https://radicalmove.github.io/radcra/*`, exact metadata endpoint `https://radicalmove.github.io/radcra/latest.json`, and exact policy URL `https://radicalmove.github.io/radcra/privacy/`. Assert the old `Beta-testing-app` URL and old em-dash product name are absent from generated manifest/runtime disclosure output.

- [ ] **Step 2: Run the focused tests and verify RED.**

  Run from `extension/`:

  ```bash
  node --test --test-concurrency=1 tests/build-config.test.ts tests/manifest.test.ts tests/update-checker.test.ts tests/overlay.test.ts tests/content.test.ts
  ```

  Expected: failures identifying the old version, product name, and public URL constants.

- [ ] **Step 3: Implement the minimal canonical identity update.** Change only the constants, public manifest source, package/lock versions, and disclosure call sites required by the failing assertions. Preserve the existing consent state machine and update-check behaviour.

- [ ] **Step 4: Run focused tests and typecheck.**

  ```bash
  node --test --test-concurrency=1 tests/build-config.test.ts tests/manifest.test.ts tests/update-checker.test.ts tests/overlay.test.ts tests/content.test.ts
  npm run typecheck
  ```

  Expected: all focused tests pass and TypeScript reports no errors.

- [ ] **Step 5: Commit.**

  ```bash
  git add extension/src extension/public/manifest.json extension/package.json extension/package-lock.json extension/tests
  git commit -m "feat: adopt final RADCRA Store identity"
  ```

### Task 2: Public policy, support page, and exact Store declarations

**Files:**
- Create: `site/support/index.html`
- Create: `docs/chrome-web-store-pre-submission-checklist.md`
- Modify: `site/index.html`
- Modify: `site/download/index.html`
- Modify: `site/privacy/index.html`
- Modify: `site/latest.json`
- Modify: `docs/privacy-policy.md`
- Modify: `docs/chrome-web-store-listing.md`
- Modify: `docs/chrome-web-store-reviewer-guide.md`
- Modify: `docs/releasing.md`
- Modify: `README.md`
- Modify: `tests/test_public_release_site.py`
- Modify: `extension/src/overlay/root.ts`
- Modify: `extension/tests/overlay.test.ts`
- Modify: `extension/tests/content.test.ts`

- [ ] **Step 1: Write failing public-site and disclosure tests.** Assert the exact lowercase homepage/privacy/support/latest URLs, `rcadavies@gmail.com`, exact five-key `latest.json` schema, `download_url` equal to `https://radicalmove.github.io/radcra/`, and repository URLs under `https://github.com/radicalmove/radcra`. Assert every authoritative public/listing file omits `Beta-testing-app` and `richard.davies@canterbury.ac.nz`.

- [ ] **Step 2: Add failing policy-alignment assertions.** Require the in-extension prominent disclosure, privacy policy, Store listing, public support page, and reviewer guide to describe the same complete data categories, GitHub Pages ordinary request metadata without Moodle content or credentials, intended authorised course-team reading, and prohibited routine operator reading. Require all nine exact Privacy dashboard category choices, remote code `No`, all Limited Use certifications, exact single-purpose text, exact short description, beta wording, category recommendation, every permission/host explanation, and the actual `webNavigation` permission with no `tabs` permission row. Require the reviewer guide's fresh-profile flow to cover disclosure/decline, acknowledgement, authentication, Moodle text and area comments, exact navigation, optional Rise/SCORM access, metadata-only update status, graceful timeout/HTTP/network failure, and sign-out.

- [ ] **Step 3: Run the focused public-site test and verify RED.**

  ```bash
  python3 -m unittest tests/test_public_release_site.py -v
  cd extension && node --test --test-concurrency=1 tests/overlay.test.ts tests/content.test.ts
  ```

  Expected: failures for stale URLs/email, missing support page, incomplete declarations, and mismatched permission text.

- [ ] **Step 4: Implement the public pages, prominent disclosure, and authoritative copy.** Create a self-contained `/support/` page using `rcadavies@gmail.com`; update the homepage, download page, privacy HTML/Markdown, in-extension disclosure, listing, reviewer guide, release guide, README, and metadata. The support page and reviewer guide must carry the same concise data-use/recipient/human-access summary and link to the full privacy policy. The support page must warn users not to email or post credentials, tokens, invitation codes, private course links, real student data, or unnecessary course content. Preserve the existing disclosure's fail-closed Continue/Decline behaviour and bounded UI.

- [ ] **Step 5: Add the exact pre-submission checklist.** Include repository rename, remote update, Pages enablement, four live URL checks, GitHub environment/secret inputs, exact Privacy dashboard selections/certifications, private trusted testers, reviewer credentials, Item ID comparison, screenshot/promo uploads, local loading of the exact ZIP, and deferred publishing.

- [ ] **Step 6: Run the focused tests and verify GREEN.**

  ```bash
  python3 -m unittest tests/test_public_release_site.py -v
  cd extension && node --test --test-concurrency=1 tests/overlay.test.ts tests/content.test.ts
  ```

  Expected: PASS.

- [ ] **Step 7: Commit.**

  ```bash
  git add site docs README.md tests/test_public_release_site.py extension/src/overlay/root.ts extension/tests/overlay.test.ts extension/tests/content.test.ts
  git commit -m "docs: align RADCRA public Store disclosures"
  ```

### Task 3: Correct icon padding and generate the small promo tile

**Files:**
- Modify: `scripts/generate-extension-icons.py`
- Create: `scripts/generate-store-assets.py`
- Modify: `scripts/requirements-build.txt` only if Pillow is not already pinned
- Modify: `extension/public/icons/icon16.png`
- Modify: `extension/public/icons/icon48.png`
- Modify: `extension/public/icons/icon128.png`
- Create: `store-assets/source/README.md`
- Create: `store-assets/radcra-promo-440x280.png`
- Create: `store-assets/README.md`
- Modify: `extension/tests/manifest.test.ts`
- Create: `tests/test_store_readiness.py`

- [ ] **Step 1: Write failing icon and promo tests.** In `manifest.test.ts`, require the 128px icon alpha bounding box to remain within `(16, 16, 112, 112)` while preserving RGBA/dimensions. In `test_store_readiness.py`, require a 440x280 RGB/RGBA PNG promo asset and reject a wrong size or missing file.

- [ ] **Step 2: Run tests and verify RED.**

  ```bash
  cd extension && node --test --test-concurrency=1 tests/manifest.test.ts
  cd .. && python3 -m unittest tests/test_store_readiness.py -v
  ```

  Expected: the current 128px alpha bounds and missing promo asset fail.

- [ ] **Step 3: Adjust the deterministic icon generator.** Draw the existing bubble mark on a 96x96 logical artboard centred inside the 128px canvas. Derive smaller icons from the same source while permitting proportionate small-size edge coverage. Regenerate all three PNGs with Pillow.

- [ ] **Step 4: Implement the deterministic promo generator.** Use Pillow and the existing icon—not generative or third-party imagery—to render a clean 440x280 teal/red tile with the exact text `RADCRA` and restrained `Course Review App` copy. Use a bundled/system font resolved explicitly, high-resolution antialiasing, no university/Google branding, and no claims.

- [ ] **Step 5: Generate and visually inspect assets.**

  ```bash
  python3 scripts/generate-extension-icons.py
  python3 scripts/generate-store-assets.py
  ```

  Inspect `extension/public/icons/icon128.png` and `store-assets/radcra-promo-440x280.png` at original size and reduced scale. Confirm transparent icon corners, legible text, consistent palette, and no clipping.

- [ ] **Step 6: Run focused tests and verify GREEN.**

  ```bash
  cd extension && node --test --test-concurrency=1 tests/manifest.test.ts
  cd .. && python3 -m unittest tests/test_store_readiness.py -v
  ```

  Expected: PASS.

- [ ] **Step 7: Commit.**

  ```bash
  git add scripts extension/public/icons extension/tests/manifest.test.ts store-assets tests/test_store_readiness.py
  git commit -m "feat: add compliant RADCRA Store artwork"
  ```

### Task 4: Fixture/submission readiness validator and package alignment

**Files:**
- Create: `deploy/scripts/store_readiness.py`
- Modify: `tests/test_store_readiness.py`
- Modify: `deploy/scripts/store_package.py`
- Modify: `tests/test_store_package.py`
- Modify: `tests/test_deployment_package.py`
- Create: `tests/fixtures/store-public-key.txt`

- [ ] **Step 1: Write failing validator-mode tests.** Define this authoritative CLI contract:

  ```bash
  python3 deploy/scripts/store_readiness.py \
    --mode fixture|submission \
    --root <repository-root> \
    --package-report <store-package.report.json> \
    --checksum <store-package.zip.sha256> \
    [--screenshot <1280x800-png>]
  ```

  `--root`, `--package-report`, and `--checksum` are required in both modes. The promo defaults to `<root>/store-assets/radcra-promo-440x280.png`; screenshot defaults to `<root>/store-assets/radcra-screenshot-1280x800.png` when that file exists. Fixture mode must return exit 0 JSON with exactly `schema_version`, `mode`, `ready`, `manual_screenshot_required`, `checks`, and `errors`; it sets `ready: true` and `manual_screenshot_required: true` when only the screenshot is absent. `checks` has exactly these boolean keys: `identity`, `public_site`, `privacy_disclosure`, `support`, `promo`, `screenshot`, `package`, `checksum`, and `production_inputs`. In fixture mode `screenshot` and `production_inputs` may be false without making `ready` false; every other check must be true. Submission mode requires every check true and exits nonzero with `ready: false` otherwise.

- [ ] **Step 2: Add failing stale/private-data and production-input tests.** Require rejection of old URL/email/name values in authoritative files, placeholder hosts or key, unexpected ZIP files, source maps, PEM/key names, direct archive `download_url`, missing production-input evidence, and screenshots with metadata or a documented sanitisation failure. Require the exact public repository identity `radicalmove/radcra`. Define a checked-in public-only RSA SPKI fixture at `tests/fixtures/store-public-key.txt`; tests/build commands may use it but must never create, locate, or accept a fixture private key.

- [ ] **Step 3: Run validator/package tests and verify RED.**

  ```bash
  python3 -m unittest tests/test_store_readiness.py tests/test_store_package.py tests/test_deployment_package.py -v
  ```

  Expected: failures because `store_readiness.py` and the new invariants do not exist.

- [ ] **Step 4: Implement the minimal readiness validator.** Keep extension ZIP validation separate from listing artwork. Read only explicitly passed paths; never glob or search for private keys. Validate exact public documents, promo/screenshot dimensions, icon alpha bounds, ZIP report/checksum, and absence of placeholder/private markers. Extend the Store package report with exact public evidence fields: `build_mode`, `build_commit`, `moodle_patterns`, `optional_frame_patterns`, `review_service_origin`, `manifest_sha256`, and `public_key_sha256`. `production_inputs` is true only when `build_mode` is `production`, `build_commit` equals the repository `HEAD`, repository/version/manifest digest match the inspected ZIP, every origin/pattern is HTTPS and contains no example/invalid placeholder, and the public-key digest matches the manifest while differing from both the checked-in development and fixture public keys. Emit the exact deterministic JSON contract from Step 1; `errors` is a sorted array of stable codes. The accepted production extension ID comparison remains a documented manual dashboard gate.

- [ ] **Step 5: Align Store package repository identity and validators.** Change default/test repository references to `radicalmove/radcra`. Add an explicit `--build-commit` package argument, verify the full commit occurs in the packaged runtime diagnostics, and write the exact public evidence fields required by Step 4. Preserve root-level manifest, deterministic timestamps/modes, runtime-only content, no source maps, and no listing images inside the ZIP.

- [ ] **Step 6: Run focused tests and verify GREEN.**

  ```bash
  python3 -m unittest tests/test_store_readiness.py tests/test_store_package.py tests/test_deployment_package.py -v
  ```

  Expected: PASS.

- [ ] **Step 7: Commit.**

  ```bash
  git add deploy/scripts/store_readiness.py deploy/scripts/store_package.py tests/test_store_readiness.py tests/test_store_package.py tests/test_deployment_package.py tests/fixtures/store-public-key.txt
  git commit -m "feat: validate RADCRA Store submission workspace"
  ```

### Task 5: GitHub Pages and release workflow alignment

**Files:**
- Modify: `.github/workflows/pages.yml`
- Modify: `.github/workflows/release-extension.yml`
- Modify: `tests/test_public_release_site.py`
- Modify: `tests/test_store_readiness.py`

- [ ] **Step 1: Write failing workflow assertions.** Require `radicalmove/radcra` in package reports, release notes, release/download links, and generated metadata. Require the release workflow to run the unit tests before building and then invoke the actual validator after creating the exact ZIP, report, per-archive checksum, promo tile, and screenshot:

  ```bash
  python3 deploy/scripts/store_readiness.py \
    --mode submission \
    --root "$GITHUB_WORKSPACE" \
    --package-report "$artifacts/radcra-web-store-v${release_version}.report.json" \
    --checksum "$artifacts/radcra-web-store-v${release_version}.zip.sha256" \
    --screenshot "$GITHUB_WORKSPACE/store-assets/radcra-screenshot-1280x800.png"
  ```

  Assert no stale repository path remains. A tagged release must stop before publishing if this command fails.

- [ ] **Step 2: Run workflow tests and verify RED.**

  ```bash
  python3 -m unittest tests/test_public_release_site.py tests/test_store_readiness.py -v
  ```

  Expected: stale workflow repository URLs and missing validator invocation fail.

- [ ] **Step 3: Update workflows.** Preserve ephemeral mode-600 PEM creation and cleanup, `BUILD_COMMIT=${{ github.sha }}`, isolated runner artifacts, server/extension/package gates, checksums, release notes, Pages deployment, and secret-free logs. Point metadata `download_url` to the public homepage and `release_url` to the tagged release page. Copy the deterministic promo and authorised screenshot only into the isolated release-assets directory, keep them outside `extension/dist` and the Web Store ZIP, and run the exact submission-validator command from Step 1 before tagged GitHub release publication. Keep the independent Pages workflow able to publish the committed `site/` artifact before a production package or screenshot exists, so the four public endpoints can be verified first.

- [ ] **Step 4: Parse YAML and run workflow tests.**

  ```bash
  python3 - <<'PY'
  from pathlib import Path
  import yaml
  for path in (Path('.github/workflows/pages.yml'), Path('.github/workflows/release-extension.yml')):
      yaml.safe_load(path.read_text(encoding='utf-8'))
      print(f'{path}: OK')
  PY
  python3 -m unittest tests/test_public_release_site.py tests/test_store_readiness.py -v
  ```

  Expected: both YAML files parse and all focused tests pass.

- [ ] **Step 5: Commit.**

  ```bash
  git add .github/workflows tests/test_public_release_site.py tests/test_store_readiness.py
  git commit -m "ci: align RADCRA Pages and Store release workflow"
  ```

### Task 6: Capture and validate the authorised real-product screenshot

**Files:**
- Create: `store-assets/radcra-screenshot-1280x800.png`
- Modify: `store-assets/README.md`

- [ ] **Step 1: Read the Chrome-control skill and inspect the current signed-in Chrome tab.** Use the existing browser session only. Do not type, reveal, or record credentials. Select a test Moodle page showing the current 0.5.36 overlay and a contextual marker/comment.

- [ ] **Step 2: Capture the real UI.** Set or crop the captured viewport to 1280x800 without distorting the interface. Prefer arranging the visible page so private details are absent rather than painting over content.

- [ ] **Step 3: Sanitize and inspect.** Remove browser chrome if it exposes personal profile data; remove or obscure unnecessary private course/user identifiers; ensure no tokens, invitation details, student records, private emails, or private URLs appear. Preserve the genuine overlay and contextual-review behaviour.

- [ ] **Step 4: Run submission artwork validation.**

  ```bash
  python3 deploy/scripts/store_readiness.py --mode submission --root . --screenshot store-assets/radcra-screenshot-1280x800.png --package-report <exact-production-report> --checksum <exact-production-checksum>
  ```

  Expected before the real production package exists: artwork checks pass and the command fails only on the documented production-package gate. If Chrome access is unavailable, omit the screenshot, keep fixture readiness green, and record the screenshot as the sole remaining artwork gate.

- [ ] **Step 5: Commit available authorised artwork.**

  ```bash
  git add store-assets
  git commit -m "docs: add RADCRA Store listing screenshot"
  ```

### Task 7: Full verification and local readiness report

**Files:**
- Create: `docs/radcra-store-readiness-report-0.5.36.md`
- Modify only if verification exposes a scoped defect.

- [ ] **Step 1: Run the full extension gates sequentially.**

  ```bash
  cd extension
  npm test
  npm run typecheck
  npm run build
  npm audit --omit=dev --audit-level=high
  ```

  Expected: 0 failures, typecheck/build success, and 0 production vulnerabilities.

- [ ] **Step 2: Run the full server suite.**

  ```bash
  cd server
  python3 -m pytest -q
  ```

  Expected: 213 tests or the current increased count pass; existing dependency deprecation warnings are documented but do not fail the suite.

- [ ] **Step 3: Run root package/site/readiness gates sequentially.**

  ```bash
  python3 -m unittest tests/test_deployment_package.py tests/test_store_package.py tests/test_public_release_site.py tests/test_release_artifacts.py tests/test_store_readiness.py
  fixture_dir="$(mktemp -d)"
  trap 'rm -rf "$fixture_dir"' EXIT
  BUILD_MODE=production \
    MOODLE_HOST_PATTERNS=https://moodle.example.org/* \
    OPTIONAL_FRAME_PATTERNS=https://rise.example.org/* \
    REVIEW_SERVICE_ORIGIN=https://review.example.org \
    EXTENSION_PUBLIC_KEY="$(tr -d '\n' < tests/fixtures/store-public-key.txt)" \
    BUILD_COMMIT="$(git rev-parse HEAD)" \
    npm --prefix extension run build
  python3 deploy/scripts/store_package.py \
    --dist extension/dist \
    --output "$fixture_dir/radcra-web-store-v0.5.36.zip" \
    --version 0.5.36 \
    --build-commit "$(git rev-parse HEAD)" \
    --repository radicalmove/radcra
  shasum -a 256 "$fixture_dir/radcra-web-store-v0.5.36.zip" > "$fixture_dir/radcra-web-store-v0.5.36.zip.sha256"
  python3 deploy/scripts/store_readiness.py \
    --mode fixture \
    --root . \
    --package-report "$fixture_dir/radcra-web-store-v0.5.36.report.json" \
    --checksum "$fixture_dir/radcra-web-store-v0.5.36.zip.sha256"
  ```

  Expected: all tests pass; fixture JSON reports ready and truthfully identifies whether the screenshot/manual production gates remain.

- [ ] **Step 4: Run production preflight without a real secret.** Use the existing preflight-only release command with an explicit non-secret placeholder path and HTTPS example service origin. It must validate required environment names without building or searching for a private key.

- [ ] **Step 5: Validate public files and git hygiene.**

  ```bash
  rg -n 'Beta-testing-app|richard\.davies@canterbury\.ac\.nz|RADCRA — Course Review' README.md docs site extension/src extension/public .github deploy/scripts tests
  git diff --check main...HEAD
  git status --short --branch
  ```

  Expected: no stale authoritative identifiers, clean diff, and only intentional commits.

- [ ] **Step 6: Write the readiness report.** Record current Google-policy sources/date, exact test results, artwork status, fixture validator result, public endpoints awaiting deployment, exact production-package inputs, and remaining external actions. State that Google retains review discretion.

- [ ] **Step 7: Request independent code review and resolve all Critical/Important findings.** Use `superpowers:requesting-code-review`, then rerun affected tests and the final sequential verification.

- [ ] **Step 8: Commit the report and any verified final corrections.**

  ```bash
  git add docs/radcra-store-readiness-report-0.5.36.md
  git commit -m "docs: record RADCRA Store readiness verification"
  ```
