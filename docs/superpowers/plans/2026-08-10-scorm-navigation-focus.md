# SCORM Navigation Focus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the Rise comment thread from undoing SCORM anchor scrolling and display `v0.5.31` in the overlay header.

**Architecture:** Retain the existing navigation pipeline and change only the final thread-focus operation to preserve scroll. Reuse build diagnostics already passed to the overlay to render the version label.

**Tech Stack:** TypeScript, Happy DOM, Node test runner, Vite.

---

### Task 1: Preserve SCORM scroll while focusing the thread

**Files:**
- Modify: `extension/tests/comment-renderer.test.ts`
- Modify: `extension/src/comment-renderer.ts`

- [ ] Add a regression test that captures the thread article's focus options and expects `{ preventScroll: true }`.
- [ ] Run `cd extension && node --test --test-concurrency=1 --test-name-pattern='thread focus preserves' tests/comment-renderer.test.ts` and verify it fails because focus currently receives no options.
- [ ] Change the final thread focus call to `article.focus({ preventScroll: true })`.
- [ ] Re-run the same focused command and verify it passes.

### Task 2: Show the installed version

**Files:**
- Modify: `extension/tests/overlay.test.ts`
- Modify: `extension/src/overlay/root.ts`

- [ ] Add a markup/style test using injected diagnostics version `7.8.9`; expect `.pilot-version` text `v7.8.9` inside `.toolbar .identity`, no build hash in that label, and the existing Help version to retain the hash. Assert the stylesheet positions `.identity` relatively and `.pilot-version` absolutely at `top:0;right:0`, with course-title padding reserving its space.
- [ ] Run `cd extension && node --test --test-concurrency=1 --test-name-pattern='visible installed version' tests/overlay.test.ts` and verify it fails because the label is absent.
- [ ] Add the escaped version label and minimal positioning styles.
- [ ] Re-run the same focused command and verify it passes.

### Task 3: Prepare and verify 0.5.31

**Files:**
- Modify: `extension/package.json`
- Modify: `extension/package-lock.json`
- Modify: release artifacts through the established release script.

- [ ] Bump the canonical package and lock versions to 0.5.31 and update the version assertion.
- [ ] Run `cd extension && npm test && npm run typecheck && npm run build`; expect exit 0 from all three commands.
- [ ] After committing the verified source so release identity is stable, run the exact established publisher command `DELIVERY_ROOT='/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds' deploy/scripts/release-pilot-extension.sh` with the deployment environment's existing `PRIVATE_KEY_PATH` and `REVIEW_SERVICE_ORIGIN` already set. If the production `extension/dist` was built separately and only publication remains, run `python3 deploy/scripts/release_artifacts.py --root "$PWD" --dist "$PWD/extension/dist" --delivery '/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds' --version 0.5.31`. Confirm `/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds/moodle-review-extension/manifest.json` reports `0.5.31`, a new immutable `/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds/releases/v0.5.31-*` directory exists, its `RELEASE.json` identifies version 0.5.31 and the release commit, and `shasum -a 256 -c SHA256SUMS` succeeds from the delivery directory.
