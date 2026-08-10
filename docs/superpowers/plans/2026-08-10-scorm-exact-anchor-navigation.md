# SCORM Exact Anchor Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a single SCORM comment selection settle on the exact text with its thread open.

**Architecture:** The renderer will scroll recovered text ranges by precise viewport geometry and report completion only when the marker/thread are visible. The existing embedded-navigation retry loop will then naturally repeat after Rise route/layout resets without a fixed delay.

**Tech Stack:** TypeScript, Happy DOM, Node test runner, Vite.

---

### Task 1: Exact text-range scrolling and idempotent visible completion

**Files:**
- Modify: `extension/tests/comment-renderer.test.ts`
- Modify: `extension/src/comment-renderer.ts`

- [ ] Add failing tests that expect a nested scroller to receive the exact range-centering delta rather than `commonAncestor.scrollIntoView`, repeated `takeToContext` calls to keep one thread open, and offscreen context to return `false` until its marker/thread are visible.
- [ ] Run `cd extension && node --test --test-concurrency=1 --test-name-pattern='exact text range|idempotent SCORM context|visible SCORM context' tests/comment-renderer.test.ts`; expect failures demonstrating the current ancestor scroll, toggle, and premature success.
- [ ] Implement a small nearest-scroll-container helper, exact range delta scrolling, and idempotent visibility-based completion.
- [ ] Re-run the focused command; expect all focused tests to pass.

### Task 2: Preserve retry state until visible

**Files:**
- Modify: `extension/tests/scorm-worker.test.ts` only if the renderer contract is not already exercised through its worker acknowledgement test.
- Modify: `extension/src/scorm-worker.ts` only if necessary to distinguish retryable offscreen context from missing projection.

- [ ] Inspect the existing `SCORM_TAKE_TO_CONTEXT` acknowledgement regression. If it already injects false then true renderer results and asserts negative then positive acknowledgements, retain it and run it unchanged; otherwise add that failing regression first.
- [ ] Run `cd extension && node --test --test-concurrency=1 --test-name-pattern='TAKE_TO_CONTEXT' tests/scorm-worker.test.ts`; expect the retained regression to pass, or the newly added regression to fail for the missing contract.
- [ ] Make the minimum worker change only if the test shows the existing acknowledgement mapping is insufficient, then re-run the focused command and expect exit 0.

### Task 3: Version, verify, and publish 0.5.32

**Files:**
- Modify: `extension/package.json`
- Modify: `extension/package-lock.json`
- Modify: `extension/tests/build-config.test.ts`

- [ ] Bump canonical version assertions to 0.5.32.
- [ ] Run `cd extension && npm test && npm run typecheck && npm run build`; expect exit 0.
- [ ] Commit the verified source, build production `extension/dist` with the currently released public extension key and deployment origin, then run `python3 deploy/scripts/release_artifacts.py --root "$PWD" --dist "$PWD/extension/dist" --delivery '/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds' --version 0.5.32`.
- [ ] In one shell execution, resolve the single immutable directory and verify it: `release_root='/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds'; release_matches=("$release_root"/releases/v0.5.32-*); [[ ${#release_matches[@]} -eq 1 && -d ${release_matches[1]} ]]; release_dir=${release_matches[1]}; python3 -c "import json,sys; from pathlib import Path; root=Path(sys.argv[1]); release=Path(sys.argv[2]); assert json.loads((root/'moodle-review-extension/manifest.json').read_text())['version']=='0.5.32'; assert json.loads((release/'RELEASE.json').read_text())['commit']==sys.argv[3]" "$release_root" "$release_dir" "$(git rev-parse HEAD)"; for name in background.js content.js manifest.json; do cmp "$release_root/moodle-review-extension/$name" "$release_dir/moodle-review-extension/$name"; done; cmp "$release_root/moodle-review-extension-chrome-edge.zip" "$release_dir/moodle-review-extension-v0.5.32-chrome-edge.zip"`; expect exit 0.
- [ ] Run `cd '/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds' && shasum -a 256 -c SHA256SUMS`; expect every entry to report `OK`.
