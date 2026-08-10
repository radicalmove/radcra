# Moodle and SCORM Navigation Settling Design

## Goal

Restore immediate comment navigation on ordinary Moodle pages while making SCORM navigation finish with the comment anchor at the vertical middle of Rise's visible scroll area and the comment box opening beside that centred marker, as in the supplied preferred screenshot.

## Root cause

Version 0.5.32 applies the same visibility-based completion contract to top-level Moodle pages and embedded SCORM content. Moodle therefore waits for retry acknowledgements that it does not need. In Rise, the contract accepts a target as soon as it is anywhere inside the nested scrollport, so a post-navigation Rise layout reset can leave the target near the bottom and still be treated as complete.

## Design

`CommentRenderer.takeToContext` will distinguish a top-level Moodle document from an embedded SCORM document through the document window relationship already used by visual-pin scrolling.

- On a top-level Moodle page, resolving the anchor, initiating the scroll, and opening the thread completes the request immediately. Scroll and resize listeners continue positioning the marker and thread as the browser scrolls. No embedded retry delay is introduced.
- In embedded SCORM, completion remains retryable and idempotent for both text highlights and visual pins. A request completes only when its recovered anchor is within 24 CSS pixels of the vertical centre of its nearest nested scrollport and the marker and thread are visible. A visible target near the bottom is not complete: another attempt recentres it.
- A text anchor uses the centre of its recovered range. A visual pin uses its recovered `y` coordinate. The requested scroll delta is `anchor centre - scrollport centre`, where scrollport centre includes `clientTop`. When there is no nested scrollport, the browser viewport midpoint is used instead.
- Direct marker clicks continue toggling threads normally; programmatic retries continue keeping the requested thread open.

The popover keeps its established placement: its top aligns with the marker and is clamped to an 8-pixel viewport margin when necessary. Centring the anchor therefore places the marker and the start of the comment box around the screen midpoint, matching the preferred screenshot; the whole box is not itself centred over and obscuring the highlighted text.

## Tests

Regression coverage will prove:

1. Top-level Moodle `takeToContext` acknowledges immediately after issuing its exact scroll, without waiting for a second call.
2. An embedded Rise text range that is visible near the bottom remains retryable and receives the exact centre-scroll delta; the viewport fallback follows the same rule.
3. The same embedded request acknowledges only once the range is within 24 pixels of centre and its marker/thread are visible, with the popover top aligned to the centred marker.
4. Embedded visual pins follow the same centre-settling contract.
5. Existing exact-range, clipping, idempotency, interaction, and worker retry tests remain green.

## Release

The verified browser-loadable release will be version 0.5.33 in the existing `Beta Testing App-pilot-builds` release folder.
