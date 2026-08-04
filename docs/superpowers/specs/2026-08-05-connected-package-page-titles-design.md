# Connected Package page-title repair

## Problem

Articulate Connected Packages contain a hidden fallback `<h1>` reading “We couldn't load this course” before the visible course heading. RADCRA currently selects the first `<h1>`, so comments are grouped under the fallback text.

Changing the page URL identity as well as the title would orphan existing markers because comment matching uses the exact stored URL.

## Agreed behaviour

- Connected Packages display the first rendered, non-empty heading; normal SCORM behaviour remains unchanged.
- Existing comments and markers stay attached to their original pages.
- Opening an affected Connected Package repairs its displayed fallback labels automatically.
- Repair is exact-page-scoped and never changes stored comments, anchors, URLs, or activity locators.
- Release this fix as extension version `0.5.30`.

## Design

Only for `packages.articulateusercontent.com`, the embedded worker derives two values:

1. **Display label:** first non-empty `<h1>` that is not `hidden`/`aria-hidden`, has a client rectangle, and whose computed `display`, `visibility`, and `opacity` do not hide it; then document title; then `Current page`.
2. **Compatibility identity:** the exact `0.5.29` algorithm—text from `document.querySelector("h1")`, otherwise document title, otherwise `Current page`. It does not scan subsequent headings.

The compatibility identity remains in the synthetic `moodle-review-page` URL hash, preserving exact marker/comment matching. The display label is used in `page_title` and the overlay.

The parent extension keeps an in-memory `(course_id, page_url) → page_title` alias from validated worker identity events. When it groups course comments, that alias overrides only the exact canonical stored fallback `Embedded activity · We couldn't load this course` for the matching course and page URL; already-correct or intentionally different titles remain untouched. Thus old labels display as `Embedded activity · <visible heading>` after that package opens, without rewriting another user's data. New comments store the corrected title normally.

Normal SCORM packages retain the exact `0.5.29` first-`<h1>` algorithm for both title and page identity.

## Safety and failure handling

- Aliases come only from validated worker events bound to the active course and exact page URL. They last for the current course-page session, are refreshed when that package reports again, and are cleared on course change or extension teardown.
- Aliasing cannot alter URLs, anchors, comment text, status, authorship, or navigation metadata.
- Aliases are rebuilt as packages open; a missing alias leaves the stored fallback label visible but does not block comments or markers.

## Verification

- Worker tests model the live zero-client-rectangle Articulate error heading followed by a visible real heading, plus explicit CSS/attribute-hidden cases.
- Compatibility tests prove existing Connected Package page URLs remain unchanged and normal SCORM is unaffected.
- Extension integration tests prove an exact-course/page alias corrects only canonical fallback labels, preserves mixed correct labels and markers, and cannot leak across course changes.
- Run the full server and extension suites, build `0.5.30`, and verify the unpacked and ZIP release artifacts.
