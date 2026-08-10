# Moodle and SCORM Comment Navigation Design

## Goal

Restore accurate same-page comment navigation on ordinary Moodle pages without weakening the improved exact-anchor navigation inside SCORM, and make SCORM's final correction feel like one movement.

## Root cause

Version 0.5.30 used native `scrollIntoView({ block: "center" })` for Moodle text anchors and element centering for Moodle pins. Later SCORM work replaced both paths with exact coordinate `scrollBy` logic. That coordinate logic is necessary for Rise's nested scrollports, but it is unreliable on ordinary Moodle layouts and sticky-page structures.

## Design

`comment-renderer.ts` will explicitly branch by browsing context.

- In the top-level Moodle document, a recovered text range will scroll its owning element with native centered `scrollIntoView`. A recovered visual pin will scroll its recovered target element with native centered `scrollIntoView`. The renderer will then focus the marker without scrolling, open the requested thread, and acknowledge completion immediately.
- In an embedded SCORM document, navigation will retain exact range/pin geometry, nearest nested scrollport detection, midpoint settling, and retry-until-visible completion.
- The first SCORM positioning request may remain smooth. If a retry finds that a correction is still needed for the same requested context, that correction will use immediate scrolling. This prevents two independently animated movements while retaining exact final centering.
- Missing anchors remain retryable/unresolved exactly as they are now. Interaction restoration, page/locator navigation, marker visibility, and thread placement remain unchanged.

## Tests

Regression tests will prove that:

1. A top-level Moodle text comment calls native centered scrolling on the recovered text owner rather than window coordinate scrolling.
2. A top-level Moodle pin calls native centered scrolling on its recovered element rather than window coordinate scrolling.
3. SCORM still scrolls the exact anchor through its nested scrollport.
4. The first SCORM movement is smooth and a subsequent correction for the same navigation is immediate.
5. Existing comment-renderer, navigation, full extension, typecheck, and production build checks pass.

## Release

Package the verified implementation as v0.5.34 in the established unpacked, ZIP, and immutable release locations. The toolbar version must read `v0.5.34`.
