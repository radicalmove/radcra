# Moodle and SCORM Comment Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore reliable centred comment jumps on ordinary Moodle pages while retaining exact SCORM navigation and removing its second visible smooth animation.

**Architecture:** Split scrolling at the renderer boundary: top-level Moodle uses native element centering, while embedded SCORM retains exact anchor geometry and nested-scrollport settling. Track the active SCORM context request so only its initial positioning uses `behavior: "smooth"`; repeat corrections use `behavior: "auto"`.

**Tech Stack:** TypeScript, Happy DOM, Node test runner, Vite, Python release tooling.

---

### Task 1: Reproduce the Moodle regression and SCORM double animation

**Files:**
- Modify: `extension/tests/comment-renderer.test.ts`

- [ ] Add a top-level Moodle text-anchor test asserting the recovered range owner receives `scrollIntoView({ block: "center", behavior: "smooth" })` and `window.scrollBy` is not called.
- [ ] Replace the current top-level pin expectation with `recovered.element.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" })` and no `window.scrollBy`.
- [ ] Add an embedded SCORM test that invokes the same unresolved context twice and expects the first exact scroll to use `behavior: "smooth"` and the correction to use `behavior: "auto"`; after simulated completion, move it away and assert a later fresh navigation to the same comment starts with `behavior: "smooth"` again.
- [ ] Run `cd extension && node --test --test-concurrency=1 --test-name-pattern='Moodle context uses native|SCORM correction' tests/comment-renderer.test.ts`; expect assertion failures against the current coordinate-only/smooth-only implementation.

### Task 2: Implement context-specific scrolling

**Files:**
- Modify: `extension/src/comment-renderer.ts`
- Test: `extension/tests/comment-renderer.test.ts`

- [ ] Add a top-level Moodle helper that recovers the exact anchor and calls native centred `scrollIntoView` on the text owner or pin element.
- [ ] Keep `anchorGeometry`, nearest nested scroller detection, midpoint visibility, and exact deltas exclusive to embedded SCORM navigation.
- [ ] Track the active embedded context request ID. Use `behavior: "smooth"` for a new request and `behavior: "auto"` for repeat corrections of that active request; clear this state when navigation is acknowledged complete, a different context is requested, or the renderer is destroyed.
- [ ] Keep marker focus with `preventScroll`, idempotent thread opening, missing-anchor recovery, and immediate top-level completion unchanged.
- [ ] Re-run the focused test command and expect pass.
- [ ] Run `cd extension && node --test --test-concurrency=1 tests/comment-renderer.test.ts`; expect zero failures.
- [ ] Commit the behavior and tests as `fix: restore Moodle comment jumps`.

### Task 3: Version, verify, and publish v0.5.34

**Files:**
- Modify: `extension/package.json`
- Modify: `extension/package-lock.json`
- Modify: `extension/tests/build-config.test.ts`

- [ ] Bump canonical version assertions from `0.5.33` to `0.5.34`; keep the source manifest placeholder unchanged.
- [ ] Run `cd extension && npm test && npm run typecheck && npm run build`; require 0 failures and exit 0.
- [ ] Run `git diff --check`; require no output.
- [ ] Request independent code review against the spec and plan, address all Critical/Important issues, and rerun affected verification.
- [ ] Commit as `release: prepare course review extension 0.5.34` and require a clean tree.
- [ ] Rebuild production `extension/dist` with this exact command and require `Production v0.5.34 identity and service origin verified`:

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
assert manifest['version']=='0.5.34' and manifest['key']==public_key
assert service_origins[0] in (root/'extension/dist/background.js').read_text()
print('Production v0.5.34 identity and service origin verified')
PY
```
- [ ] Publish exactly: `python3 deploy/scripts/release_artifacts.py --root "$PWD" --dist "$PWD/extension/dist" --delivery '/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds' --version 0.5.34`.
- [ ] Verify exactly one `/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds/releases/v0.5.34-*`, stable manifest version `0.5.34`, release commit equals `HEAD`, stable and immutable `background.js`, `content.js`, and `manifest.json` compare equal, ZIPs compare equal, and `(cd '/Users/rcd58/OpenAI Projects/Beta Testing App-pilot-builds' && shasum -a 256 -c SHA256SUMS)` reports every file `OK`.
