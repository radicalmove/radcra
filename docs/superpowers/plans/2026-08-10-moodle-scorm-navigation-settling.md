# Moodle and SCORM Navigation Settling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore immediate Moodle comment jumps and make embedded SCORM comments settle at the vertical midpoint with their threads open.

**Architecture:** Extend the renderer's existing anchor geometry helpers so both text highlights and visual pins expose an anchor point and nearest nested scrollport. Top-level Moodle acknowledges after initiating navigation; embedded SCORM acknowledges only when the anchor is within 24 CSS pixels of the relevant midpoint and marker/thread visibility is confirmed.

**Tech Stack:** TypeScript, Happy DOM, Node test runner, Vite, Python release tooling.

---

### Task 1: Reproduce Moodle delay and SCORM bottom settling

**Files:**
- Modify: `extension/tests/comment-renderer.test.ts`

- [ ] Add a top-level Moodle regression that places an anchor offscreen, asserts `takeToContext` returns `true` on the first call, and asserts the exact scroll request is issued.
- [ ] Add embedded text-highlight regressions with a visible anchor more than 24 pixels below the nested scrollport midpoint. Assert the first call returns `false`, requests the exact centring delta, and a subsequent centred geometry returns `true` without closing the thread.
- [ ] Add two equivalent embedded visual-pin regressions: one for an exact nested scrollport delta and one for the no-nested-scrollport viewport fallback.
- [ ] In the centred embedded regressions, assert that the popover top aligns with the marker top and that an edge-positioned marker clamps the popover to the established 8-pixel viewport margin.
- [ ] Run `cd extension && node --test --test-force-exit --test-concurrency=1 --test-name-pattern='Moodle context completes immediately|SCORM text context settles at centre|SCORM pin context settles at centre' tests/comment-renderer.test.ts`.
- [ ] Confirm the new tests fail because Moodle currently returns `false` and embedded visibility currently accepts bottom-positioned anchors.

### Task 2: Implement split completion and exact centre settling

**Files:**
- Modify: `extension/src/comment-renderer.ts`
- Test: `extension/tests/comment-renderer.test.ts`

- [ ] Add an anchor-geometry helper returning the recovered anchor's vertical coordinate and nearest nested vertical scroller: range midpoint for text, recovered `y` for pins.
- [ ] Reuse the exact delta `anchorY - (scrollerRect.top + scroller.clientTop + scroller.clientHeight / 2)` for nested scrollers, or `anchorY - view.innerHeight / 2` for the viewport fallback.
- [ ] Add an embedded centre predicate using `Math.abs(anchorY - midpoint) <= 24`.
- [ ] In `takeToContext`, preserve anchor resolution, exact scrolling, focus, and idempotent thread opening. Return `true` immediately after these actions when `view.top === view`; for embedded documents return `true` only when marker/thread visibility and the centre predicate both pass.
- [ ] Keep direct marker-click toggling unchanged.
- [ ] Re-run the focused command from Task 1 and expect all three regressions to pass.
- [ ] Run `cd extension && node --test --test-force-exit --test-concurrency=1 --test-name-pattern='takeToContext|top-level Moodle navigation|nested SCORM|previous and next' tests/comment-renderer.test.ts` and expect exit 0.
- [ ] Run `cd extension && npm run typecheck` and expect exit 0.

### Task 3: Verify and publish v0.5.33

**Files:**
- Modify: `extension/package.json`
- Modify: `extension/package-lock.json`
- Modify: `extension/tests/build-config.test.ts`

- [ ] Bump the canonical package, lock, and build-config assertion from `0.5.32` to `0.5.33`; keep the source manifest placeholder unchanged.
- [ ] Run `cd extension && node --test --test-force-exit --test-concurrency=1 tests/*.test.ts`; require zero failures.
- [ ] Run `cd extension && npm run typecheck`; require exit 0.
- [ ] Run `cd extension && npm run build`; require exit 0.
- [ ] Run `git diff --check`; require exit 0 and no output.
- [ ] Request an independent code review against this plan and specification; resolve every Critical or Important issue and rerun affected verification.
- [ ] Commit the verified implementation and version bump.
- [ ] Build production `extension/dist` and verify identity/version with the following self-contained command; require exit 0 and the final verification message:

```bash
python3 - <<'PY'
import json, os, re, subprocess
from pathlib import Path
root=Path.cwd()
delivery=Path('/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds/moodle-review-extension')
released_manifest=json.loads((delivery/'manifest.json').read_text())
public_key=released_manifest['key']
origins=sorted(set(re.findall(r'https://[A-Za-z0-9.-]+', (delivery/'background.js').read_text())))
service_origins=[origin for origin in origins if origin not in {'https://my.uconline.ac.nz','https://packages.articulateusercontent.com'}]
assert len(service_origins)==1
patterns=','.join(line.strip() for line in (root/'deploy/config/pilot-optional-frame-patterns.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))
env=os.environ.copy()
env.update({'EXTENSION_PUBLIC_KEY':public_key,'MOODLE_HOST_PATTERNS':'https://my.uconline.ac.nz/*','OPTIONAL_FRAME_PATTERNS':patterns,'REVIEW_SERVICE_ORIGIN':service_origins[0],'BUILD_MODE':'production','BUILD_COMMIT':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()})
subprocess.run(['npm','run','build'],cwd=root/'extension',env=env,check=True)
manifest=json.loads((root/'extension/dist/manifest.json').read_text())
assert manifest['version']=='0.5.33' and manifest['key']==public_key
assert service_origins[0] in (root/'extension/dist/background.js').read_text()
print('Production v0.5.33 identity and service origin verified')
PY
```
- [ ] Publish with `python3 deploy/scripts/release_artifacts.py --root "$PWD" --dist "$PWD/extension/dist" --delivery '/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds' --version 0.5.33`.
- [ ] Verify the single immutable release and compatibility artifacts with the following command; require exit 0 and every checksum to report `OK`:

```zsh
setopt errexit null_glob
release_root='/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds'
release_matches=("$release_root"/releases/v0.5.33-*)
[[ ${#release_matches[@]} -eq 1 && -d ${release_matches[1]} ]]
release_dir=${release_matches[1]}
python3 -c "import json,sys; from pathlib import Path; root=Path(sys.argv[1]); release=Path(sys.argv[2]); assert json.loads((root/'moodle-review-extension/manifest.json').read_text())['version']=='0.5.33'; assert json.loads((release/'RELEASE.json').read_text())['commit']==sys.argv[3]" "$release_root" "$release_dir" "$(git rev-parse HEAD)"
for name in background.js content.js manifest.json; do cmp "$release_root/moodle-review-extension/$name" "$release_dir/moodle-review-extension/$name"; done
cmp "$release_root/moodle-review-extension-chrome-edge.zip" "$release_dir/moodle-review-extension-v0.5.33-chrome-edge.zip"
cd "$release_root"
shasum -a 256 -c SHA256SUMS
```
