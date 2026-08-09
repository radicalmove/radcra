# SCORM Navigation Focus Design

## Goal

Keep Rise SCORM navigation settled on the selected comment and show the installed extension version in the overlay header.

## Diagnosis

Live tracing on SOWK610-SOWK303-26S2 showed that choosing the 1.1.3 comment changes to the correct Rise lesson and initially scrolls its nested `.page-wrap` to the recovered anchor. Opening the fixed comment thread then focuses the thread without `preventScroll`, which moves the nested scroller back toward the top. Native Rise lesson navigation does not exhibit that reset.

## Design

- Preserve accessible focus on the opened comment thread, but call `focus({ preventScroll: true })` so it cannot undo the anchor scroll.
- Keep the existing route, retry, anchor recovery, and smooth-scroll logic unchanged.
- Render a quiet, always-visible `v<version>` label at the top-right of the turquoise toolbar. Keep the build hash only in Help.
- Release as 0.5.31.

## Verification

- Regression test that an opened thread receives focus with `preventScroll`.
- Markup/style test for the visible version label.
- Full extension tests, typecheck, and production build.

