# Sphere public guide implementation plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution of the user-approved structure.

**Goal:** Publish detailed, scannable Sphere installation/access instructions that match the tested product.

**Architecture:** Three static HTML pages share local CSS and the existing Sphere PNG. The support page is the canonical guide; home and download pages provide clear entry paths. No application behavior changes.

**Tech Stack:** HTML/CSS, Python HTMLParser/pytest, Playwright/Chromium, GitHub Actions/Pages.

## 1. Test the contract first

- [ ] Extend `tests/test_public_release_site.py` with an HTMLParser collecting IDs, links, scripts, image and CSS assets. Require a guide section menu, expected-result notes, nine stable sections, valid local fragment targets, one H1 per page and self-hosted assets. Run targeted pytest and observe missing-feature failures.
- [ ] Create `extension/e2e/public-guide.spec.ts`, opt-in via `SPHERE_PUBLIC_GUIDE=1`, using a loopback-only static site at48146. Check the three pages at1280px and390px, logo loading, no horizontal document overflow, guide jump links and visible keyboard focus. Save screenshots under Playwright outputs.

## 2. Implement the approved layout

- [ ] Add `site/assets/site.css` and reuse `server/app/static/sphere-logo.png` as `site/assets/sphere-logo.png` without altering the original.
- [ ] Rewrite `site/support/index.html` into the approved guide, preserving privacy disclosure text and `#getting-started`. Use expected-result callouts, returning/new-device guidance, explicit disable→verify→remove legacy instructions, accurate role descriptions, role-specific course-team notes and detailed troubleshooting disclosures.
- [ ] Update `site/index.html` and `site/download/index.html` to the shared brand/navigation, one primary Store action and clear guide/returning/old-pilot routes. Retain beta warning, canonical privacy/support/metadata URLs and no phantom ZIP links.

## 3. Verify and publish

- [ ] Run `PATH="$PWD/.venv/bin:$PATH" ./.venv/bin/python -m pytest -q tests` with the pinned build dependencies.
- [ ] Serve only `site/` through Python http.server bound127.0.0.1:48146. Run the opt-in Playwright tests and inspect screenshots; stop that owned process afterwards.
- [ ] Request independent review of content accuracy, accessibility, link resolution and no extraneous application changes. Fix any blockers.
- [ ] Commit only explicit guide file paths and push the feature branch. Integrate the same exact website/doc/test blobs into main without disturbing unrelated files/worktrees. Verify the workflow, final Pages build and actual live guide/CSS/logo responses.
- [ ] Record evidence and give the user the live guide link. Leave the Store version/backend/data/permissions unchanged.

## Execution record — 18 November 2026

All implementation and publication steps above are complete. The final guide has eleven linked sections. Tests first failed for the missing layout/assets; review also caught a missing explicit Send sign-in link step, which was added with a red/green regression assertion.

- Fresh root suite: 70 passed; isolated Chromium desktop/mobile suite: 8 passed. Screenshots inspected at 1280px and 390px; keyboard focus, jump navigation, FAQ expansion, logo loading, local links, no horizontal overflow and no third-party page requests checked.
- Independent review approved after the sign-in clarification; `git diff --check` passed.
- Implementation: `fda89df`; website-only main integration: `08348926ba2da66b373587437f510eb3141272aa` (six explicitly selected paths; no application code).
- Publishing workflow: run `44169810890` succeeded. Final public Pages build `998a4fbf22da1b8a0471b2a33a7808f788a25429` reached `built`, with no error.
- Live home, download, support, stylesheet and logo responses matched the tested local files byte-for-byte using SHA-256. Owned loopback test server stopped afterwards.
- Store extension, backend, live course data and permissions unchanged. Preexisting `extension/src/overlay/root.ts` edit excluded and preserved.
