# Connected Package Page Titles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display real Articulate Connected Package headings, retain every existing marker/page identity, and publish pilot extension `0.5.30`.

**Architecture:** `scorm-worker.ts` keeps the exact 0.5.29 identity algorithm but selects a rendered heading for the display title only on the exact Articulate host. A small pure alias module lets the top-frame content controller display that corrected title for legacy fallback comments at the same course and page URL without changing server data.

**Tech Stack:** TypeScript, Chrome Manifest V3, Node test runner, Happy DOM, Playwright, Vite, existing signed release scripts.

---

### Task 1: Correct Connected Package display identity without changing marker identity

**Files:**
- Modify: `extension/src/scorm-worker.ts`
- Test: `extension/tests/scorm-worker.test.ts`

- [ ] **Step 1: Write failing identity tests**

Add tests for an Articulate document containing a zero-rectangle fallback `<h1>` followed by a rendered real `<h1>`. Stub `getClientRects()` and `getComputedStyle()` as needed. Assert:

```ts
assert.equal(identity.pageTitle, "Embedded activity · 1.1.1 Course foundations and defining crime and deviance");
assert.equal(new URL(identity.pageUrl).hash, "#moodle-review-page=We%20couldn't%20load%20this%20course");
```

Also cover `hidden`, `aria-hidden="true"`, `display:none`, `visibility:hidden`, and `opacity:0`, plus a non-Articulate URL proving the exact first-`h1` 0.5.29 behaviour remains unchanged.

- [ ] **Step 2: Run RED**

```sh
cd extension
node --test --test-concurrency=1 --test-name-pattern="Connected Package.*heading|normal SCORM.*legacy" tests/scorm-worker.test.ts
```

Expected: the Connected Package title assertions fail with `Embedded activity · We couldn't load this course`.

- [ ] **Step 3: Implement the minimal host-specific selector**

Keep a `legacyPageLabel(document)` matching 0.5.29 exactly. Add a rendered-heading predicate and use it only when `window.location.hostname === "packages.articulateusercontent.com"`. `embeddedPageIdentity` uses the legacy label for the synthetic URL and the rendered label for `pageTitle` on that host; all other hosts use the legacy label for both.

- [ ] **Step 4: Run GREEN and commit**

```sh
cd extension
node --test --test-concurrency=1 tests/scorm-worker.test.ts
npm run typecheck
cd ..
git add extension/src/scorm-worker.ts extension/tests/scorm-worker.test.ts
git commit -m "fix: use visible Connected Package page titles"
```

Expected: tests and typecheck pass.

### Task 2: Alias existing fallback labels in the active course session

**Files:**
- Create: `extension/src/connected-package-title-aliases.ts`
- Create: `extension/tests/connected-package-title-aliases.test.ts`
- Modify: `extension/src/content.ts`
- Test: `extension/tests/content.test.ts`

- [ ] **Step 1: Write failing pure projection tests**

Specify a narrow API:

```ts
recordConnectedPackageTitleAlias(aliases, activeCourseId, event): boolean
applyConnectedPackageTitleAliases(comments, courseId, aliases): PageComment[]
```

Assert an alias is accepted only for HTTPS `packages.articulateusercontent.com`, the exact synthetic fallback hash, a matching course ID, and a corrected `Embedded activity · …` title. Assert projection replaces only the exact canonical stored fallback title for the exact `(course_id, page_url)`, leaves mixed correct titles and all marker/navigation fields untouched, and does not leak to another course.

- [ ] **Step 2: Run RED**

```sh
cd extension
node --test --test-concurrency=1 tests/connected-package-title-aliases.test.ts
```

Expected: failure because the module does not exist.

- [ ] **Step 3: Implement the pure alias module**

Use an in-memory map keyed by an unambiguous course/page key. Parse and validate the URL; decode the `moodle-review-page` hash and require exactly `We couldn't load this course`. Return original comment objects except canonical fallback rows that need a copied `page_title`.

- [ ] **Step 4: Run focused module tests GREEN**

```sh
cd extension
node --test --test-concurrency=1 tests/connected-package-title-aliases.test.ts
```

Expected: all pass.

- [ ] **Step 5: Write a failing content-controller integration test**

Extend the existing runtime harness to deliver a validated `SCORM_PAGE_IDENTITY_CHANGED` event. Assert the current legacy comments are immediately re-rendered with the corrected title, while the unmodified comments sent back to the worker retain their exact page URLs and marker data. Also assert aliases clear on a course change/cleanup.

- [ ] **Step 6: Run integration test RED**

```sh
cd extension
node --test --test-concurrency=1 --test-name-pattern="Connected Package title alias" tests/content.test.ts
```

Expected: old fallback title remains visible.

- [ ] **Step 7: Wire aliases into `startCourseReview`**

Maintain the alias map beside `latestComments`. On a matching identity event, record the alias and call `overlay.setCommentList(applyConnectedPackageTitleAliases(...))`; continue sending the untouched `latestComments` to the worker. Apply aliases on every later course-comment render. Clear aliases when the course changes and on teardown.

- [ ] **Step 8: Run GREEN and commit**

```sh
cd extension
node --test --test-concurrency=1 tests/connected-package-title-aliases.test.ts tests/content.test.ts
npm run typecheck
cd ..
git add extension/src/connected-package-title-aliases.ts extension/tests/connected-package-title-aliases.test.ts extension/src/content.ts extension/tests/content.test.ts
git commit -m "fix: repair legacy Connected Package labels"
```

Expected: focused tests and typecheck pass.

### Task 3: Prepare pilot version 0.5.30

**Files:**
- Modify: `extension/tests/build-config.test.ts`
- Modify: `extension/e2e/version-layout.spec.ts`
- Modify: `tests/test_deployment_package.py`
- Modify: `docs/pilot-test-script.md`
- Modify: `docs/operations.md`
- Modify: `extension/package.json`
- Modify: `extension/package-lock.json`

- [ ] **Step 1: Change version expectations to 0.5.30 and run RED**

Update test expectations first, leaving package metadata at 0.5.29.

```sh
cd extension
node --test --test-concurrency=1 tests/build-config.test.ts
cd ..
python3 -m unittest tests/test_deployment_package.py
```

Expected: failures reporting 0.5.29 instead of 0.5.30.

- [ ] **Step 2: Bump metadata and pilot instructions**

Set only the root package versions in `extension/package.json` and both root fields in `extension/package-lock.json` to `0.5.30`. Update the active pilot instructions to test a normal SCORM package and a Connected Package containing existing fallback-labelled comments. Update operations wording to describe the Connected Package safeguards as applying from 0.5.29 onward.

- [ ] **Step 3: Run version checks GREEN and commit**

```sh
cd extension
node --test --test-concurrency=1 tests/build-config.test.ts
npm run test:e2e -- e2e/version-layout.spec.ts
cd ..
python3 -m unittest tests/test_deployment_package.py
git add extension/package.json extension/package-lock.json extension/tests/build-config.test.ts extension/e2e/version-layout.spec.ts tests/test_deployment_package.py docs/pilot-test-script.md docs/operations.md
git commit -m "release: prepare pilot extension 0.5.30"
```

Expected: version, layout, and deployment checks pass.

### Task 4: Review, verify, and publish immutable 0.5.30 artifacts

**Files:**
- No tracked source changes expected
- Publish outside Git: `/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds/`

- [ ] **Step 1: Run implementation and specification reviews**

Use `superpowers:requesting-code-review` and resolve any material findings. Then run `git diff --check` and confirm the worktree is clean.

- [ ] **Step 2: Run fresh serial verification**

```sh
npm --prefix extension test
npm --prefix extension run typecheck
npm --prefix extension run test:e2e -- e2e/version-layout.spec.ts
(cd server && python3 -m pytest -q)
python3 -m unittest tests/test_release_artifacts.py tests/test_deployment_package.py
```

Expected: zero failures.

- [ ] **Step 3: Push the verified source and check service health**

```sh
git push origin HEAD:feature/moodle-course-review
curl -fsS --max-time 10 https://satin-childrens-ellen-jaguar.trycloudflare.com/health
```

Expected: push succeeds and health returns `{"status":"ok"}`. Stop before publication if either fails.

- [ ] **Step 4: Publish signed artifacts**

```sh
PRIVATE_KEY_PATH='/Users/rcd58/.config/moodle-review/pilot-extension.pem' \
REVIEW_SERVICE_ORIGIN='https://satin-childrens-ellen-jaguar.trycloudflare.com' \
deploy/scripts/release-pilot-extension.sh
```

Expected: an immutable `0.5.30` release, stable unpacked folder, and versioned ZIP are published in the existing delivery root.

- [ ] **Step 5: Verify the release and hand off**

Verify `RELEASE.json` and unpacked `manifest.json` report `0.5.30`; optional permissions remain exactly `https://packages.articulateusercontent.com/*`; `SHA256SUMS` passes; the worktree remains clean; and the prior 0.5.29 ZIP is unchanged. Provide the user a clickable link to `moodle-review-extension-v0.5.30-chrome-edge.zip` and concise reload/test steps.
