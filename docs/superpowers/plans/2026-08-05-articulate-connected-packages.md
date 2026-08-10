# Articulate Connected Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish RADCRA pilot extension 0.5.29 with permission-gated review support inside Articulate Rise Connected Packages hosted at `packages.articulateusercontent.com`.

**Architecture:** Extend the existing top-frame SCORM discovery so it recursively traverses accessible Moodle-hosted wrapper documents and reports inaccessible nested origins. Keep Chrome access optional and exact-host, then reuse the existing permission, dynamic injection, frame election, and embedded-capability flows. Sanitize the observed Connected Package launcher token at embedded locator derivation, without changing ordinary Rise route hashes.

**Tech Stack:** TypeScript, Chrome Manifest V3 permissions/scripting APIs, Happy DOM and Node test runner, Vite, Playwright, Python deployment tests, Bash release scripts.

---

### Task 1: Discover a Connected Package iframe through its Moodle launcher

**Files:**
- Modify: `extension/tests/content.test.ts`
- Modify: `extension/src/content.ts`

- [ ] **Step 1: Write failing recursive-discovery tests**

Import `inaccessibleFrameOrigins` in `extension/tests/content.test.ts`. Add one focused unit test that creates:

```ts
const top = new Window({ url: "https://my.uconline.ac.nz/mod/scorm/player.php?id=22" });
const launcher = new Window({ url: "https://my.uconline.ac.nz/pluginfile.php/1/mod_scorm/content/22/scormcontent/indexAPI.html" });
top.document.body.innerHTML = '<iframe id="launcher"></iframe>';
launcher.document.body.innerHTML = '<iframe id="connected" src="https://packages.articulateusercontent.com/content/example/boot.html#token=synthetic"></iframe>';
Object.defineProperty(top.document.querySelector("#launcher")!, "contentDocument", { value: launcher.document });
Object.defineProperty(launcher.document.querySelector("#connected")!, "contentDocument", { value: null });
assert.deepEqual(inaccessibleFrameOrigins(top.document as unknown as Document), ["https://packages.articulateusercontent.com"]);
assert.equal(countInaccessibleFrames(top.document as unknown as Document), 1);
```

Add a cycle-safety assertion by making an accessible descendant iframe point back to `top.document`; the same Articulate origin must be reported once and traversal must terminate.

In the same red phase, add a `startCourseReview` test using the top → accessible launcher → inaccessible Articulate tree, with optional patterns set to only `https://packages.articulateusercontent.com/*`. Resolve the course successfully, return no granted optional patterns from `GET_REVIEW_FRAME_STATUS`, wait for the frame poll, and assert:

- the overlay presents **Allow SCORM review access**;
- clicking it sends exactly `{ type: "REQUEST_SCORM_PERMISSION", origin: "https://packages.articulateusercontent.com" }`;
- no broader or Moodle origin is requested.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```sh
cd extension
node --test --test-name-pattern="Connected Package|recursive" tests/content.test.ts
```

Expected: both new tests FAIL because `countInaccessibleFrames` and `inaccessibleFrameOrigins` inspect only direct child iframes, so the nested permission candidate is never found.

- [ ] **Step 3: Implement cycle-safe recursive traversal**

In `extension/src/content.ts`, add one internal traversal helper that:

- starts from the supplied document;
- stores visited `Document` objects in a `Set<Document>`;
- reads each iframe's `contentDocument` inside `try/catch`;
- recurses only into non-null accessible documents;
- reports an inaccessible iframe through a callback;
- never reads the body or DOM of an inaccessible child.

Use it in both `countInaccessibleFrames` and `inaccessibleFrameOrigins`. Deduplicate origins while preserving first-observed order. Continue returning `"null"` for an unparseable inaccessible iframe URL.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the same focused command. Expected: all selected tests PASS.

- [ ] **Step 5: Commit Task 1**

```sh
git add extension/src/content.ts extension/tests/content.test.ts
git commit -m "feat: discover nested Connected Package frames"
```

### Task 2: Prevent launcher tokens from entering comment location data

**Files:**
- Modify: `extension/tests/scorm-worker.test.ts`
- Modify: `extension/tests/background-bridge.test.ts`
- Modify: `extension/src/scorm-worker.ts`

- [ ] **Step 1: Write a failing token-sanitization test**

Create a worker at a synthetic Connected Package URL such as:

```ts
https://packages.articulateusercontent.com/content/example/boot.html#token=synthetic-secret
```

Give the document meaningful selectable content, capture a text anchor, and assert:

- the initial page URL uses the existing `moodle-review-page=...` identity and contains neither `token` nor `synthetic-secret`;
- `SCORM_ANCHOR_CAPTURED.payload.embedded_locator` equals `/content/example/boot.html`;
- the full emitted event JSON contains neither `token` nor `synthetic-secret`.

Add a companion assertion that `#/lessons/one` remains the locator for an ordinary Rise route.

In `extension/tests/background-bridge.test.ts`, import `embeddedPageIdentity` and create a Happy DOM window at the same synthetic launch URL. Build the claim from that function's current `pageUrl` and `embeddedLocator`, invoke `handleCreateEmbeddedCommentBridge`, capture the payload passed to its `create` dependency, and assert the locator is `/content/example/boot.html` and the serialized API payload contains neither the `token` key nor `synthetic-secret`. Before the sanitizer exists this test fails because the derived claim carries the launcher fragment; afterward it verifies the final request boundary in addition to the worker event boundary.

- [ ] **Step 2: Run the focused test and verify RED**

```sh
cd extension
node --test --test-name-pattern="launcher token" tests/scorm-worker.test.ts tests/background-bridge.test.ts
```

Expected: FAIL because the current embedded locator preserves `#token=synthetic-secret`.

- [ ] **Step 3: Implement the minimal locator sanitizer**

In `extension/src/scorm-worker.ts`, derive the locator from a `URL` as follows:

```ts
const fragment = current.hash.slice(1);
const launcherToken = new URLSearchParams(fragment).has("token");
const embeddedLocator = !launcherToken && current.hash
  ? current.hash
  : `${current.pathname}${current.search}` || "/";
```

Use this helper only in `embeddedPageIdentity`. Do not alter the existing RADCRA page identity hash or ordinary Rise route handling.

- [ ] **Step 4: Run focused and protocol-adjacent tests**

```sh
cd extension
node --test --test-name-pattern="launcher token|Connected Package API payload|selectionchange caches|apply-locator" tests/scorm-worker.test.ts tests/background-bridge.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```sh
git add extension/src/scorm-worker.ts extension/tests/scorm-worker.test.ts extension/tests/background-bridge.test.ts
git commit -m "fix: exclude Connected Package launcher tokens"
```

### Task 3: Approve only the observed Articulate package host

**Files:**
- Modify: `tests/test_deployment_package.py`
- Modify: `deploy/config/pilot-optional-frame-patterns.txt`
- Modify: `docs/operations.md`
- Modify: `docs/pilot-test-script.md`

- [ ] **Step 1: Replace the obsolete empty-config test with a failing exact-host test**

In `tests/test_deployment_package.py`, replace `test_empty_optional_pattern_config_is_intentional_and_evidence_backed` with a test that requires the non-comment configuration lines to equal exactly:

```python
["https://packages.articulateusercontent.com/*"]
```

Require the comments to mention an observed Articulate Rise Connected Package and prohibit wildcard Articulate hosts such as `https://*.articulateusercontent.com/*`.

- [ ] **Step 2: Run the deployment test and verify RED**

```sh
python3 -m unittest tests.test_deployment_package.DeploymentPackageTests.test_connected_package_optional_pattern_is_exact_and_evidence_backed
```

Expected: FAIL because the reviewed configuration is still intentionally empty.

- [ ] **Step 3: Update the reviewed pilot configuration**

Replace the empty-config comments with concise evidence comments and the exact line:

```text
https://packages.articulateusercontent.com/*
```

Do not modify the release script's exact-file enforcement or add another host.

- [ ] **Step 4: Run configuration and permission tests**

```sh
python3 -m unittest tests.test_deployment_package.DeploymentPackageTests.test_connected_package_optional_pattern_is_exact_and_evidence_backed tests.test_deployment_package.DeploymentPackageTests.test_release_uses_the_exact_reviewed_optional_frame_pattern_file
cd extension
node --test tests/optional-content-scripts.test.ts tests/optional-permissions.test.ts tests/manifest.test.ts
```

Expected: PASS.

- [ ] **Step 5: Document reviewer and operator behaviour**

Add a short Connected Packages subsection to `docs/operations.md` and a manual check to `docs/pilot-test-script.md` covering:

- the exact supported host;
- the persistent-until-revoked permission grant;
- denial and reload-required states;
- ordinary SCORM remaining unchanged;
- remote Articulate updates potentially invalidating anchors;
- a test marker and text comment that are confirmed after reload and then deleted.

- [ ] **Step 6: Commit Task 3**

```sh
git add deploy/config/pilot-optional-frame-patterns.txt tests/test_deployment_package.py docs/operations.md docs/pilot-test-script.md
git commit -m "feat: allow reviewed Articulate package frames"
```

### Task 4: Prepare canonical pilot version 0.5.29

**Files:**
- Modify: `extension/package.json`
- Modify: `extension/package-lock.json`
- Modify: `extension/tests/build-config.test.ts`
- Modify: `extension/e2e/version-layout.spec.ts`

- [ ] **Step 1: Write the failing version expectations**

Change the expected canonical version in `extension/tests/build-config.test.ts` and Help diagnostic text in `extension/e2e/version-layout.spec.ts` from `0.5.28` to `0.5.29`, without changing package files yet.

- [ ] **Step 2: Run version checks and verify RED**

```sh
cd extension
node --test --test-name-pattern="canonical package|generated manifest" tests/build-config.test.ts
npm run test:e2e -- e2e/version-layout.spec.ts
```

Expected: version assertions FAIL against 0.5.28.

- [ ] **Step 3: Bump package and lock versions**

Change only the root package versions in `extension/package.json`, `extension/package-lock.json`, and `extension/package-lock.json`'s `packages[""]` entry to `0.5.29`.

- [ ] **Step 4: Run focused version checks GREEN**

Run the same commands. Expected: both Node version tests and both Playwright layout checks PASS.

- [ ] **Step 5: Commit Task 4**

```sh
git add extension/package.json extension/package-lock.json extension/tests/build-config.test.ts extension/e2e/version-layout.spec.ts
git commit -m "release: prepare pilot extension 0.5.29"
```

### Task 5: Full verification and immutable publication

**Files:**
- No tracked source changes expected.
- Publish outside Git: `/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds/`

- [ ] **Step 1: Verify the implementation diff and clean branch**

```sh
git diff --check
git status --short --branch
git log --oneline -8
```

Expected: no uncommitted files and the Task 1–4 commits at HEAD.

- [ ] **Step 2: Record the immutable 0.5.28 artifact identity**

Record the resolved path and SHA-256 of:

```text
/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds/moodle-review-extension-v0.5.28-chrome-edge.zip
```

Do this before publishing 0.5.29. Keep the value in the execution log, not a tracked file.

- [ ] **Step 3: Run fresh serial verification**

Run serially because extension and deployment builds both write `extension/dist`:

From the repository root, run each command separately and wait for it to finish before starting the next:

```sh
npm --prefix extension test
npm --prefix extension run typecheck
npm --prefix extension run test:e2e -- e2e/version-layout.spec.ts
(cd server && python3 -m pytest -q)
python3 -m unittest tests/test_release_artifacts.py tests/test_deployment_package.py
```

Expected: zero failures. Record exact pass/skip totals.

- [ ] **Step 4: Push the verified source before immutable publication**

```sh
git push origin HEAD:feature/moodle-course-review
```

Expected: the remote branch contains the exact clean commit that the release metadata will record. If the push fails, stop before publishing.

- [ ] **Step 5: Verify the public review service before release**

```sh
curl -fsS --max-time 10 https://satin-childrens-ellen-jaguar.trycloudflare.com/health
```

Expected: `{"status":"ok"}`.

- [ ] **Step 6: Publish the signed 0.5.29 package**

From the clean repository root:

```sh
PRIVATE_KEY_PATH='/Users/rcd58/.config/moodle-review/pilot-extension.pem' \
REVIEW_SERVICE_ORIGIN='https://satin-childrens-ellen-jaguar.trycloudflare.com' \
deploy/scripts/release-pilot-extension.sh
```

Expected: the release script repeats its internal tests, builds a production manifest containing only the configured Moodle host, service host, and exact optional Articulate host, then publishes verified artifacts under the existing pilot-builds directory.

- [ ] **Step 7: Verify 0.5.29 and prove 0.5.28 unchanged**

Verify:

- `RELEASE.json` and unpacked `manifest.json` report 0.5.29;
- `manifest.json.optional_host_permissions` equals `["https://packages.articulateusercontent.com/*"]`;
- `shasum -a 256 -c SHA256SUMS` passes in the current release;
- `moodle-review-extension-v0.5.29-chrome-edge.zip` exists;
- the 0.5.28 ZIP still exists and its SHA-256 exactly matches the value recorded in Step 2;
- the worktree remains clean.

- [ ] **Step 8: Hand off the manual Moodle check**

Provide the user a clickable link to the versioned 0.5.29 ZIP and concise steps: replace/reload the unpacked extension, verify **Pilot 0.5.29**, open the supplied Connected Package activity, approve **Allow SCORM review access**, reload if requested, create and verify one marker plus one text comment, then delete those temporary comments.

No server restart is required because this release changes only the extension, tests, configuration, and documentation.
