# Moodle and SCORM Navigation Settling Design

## Goal

Restore immediate comment navigation on ordinary Moodle pages while making SCORM navigation finish with the highlighted content and its comment box around the vertical middle of Rise's visible scroll area.

## Root cause

Version 0.5.32 applies the same visibility-based completion contract to top-level Moodle pages and embedded SCORM content. Moodle therefore waits for retry acknowledgements that it does not need. In Rise, the contract accepts a target as soon as it is anywhere inside the nested scrollport, so a post-navigation Rise layout reset can leave the target near the bottom and still be treated as complete.

## Design

`CommentRenderer.takeToContext` will distinguish a top-level Moodle document from an embedded SCORM document through the document window relationship already used by visual-pin scrolling.

- On a top-level Moodle page, resolving the anchor, initiating the scroll, and opening the thread completes the request immediately. Scroll and resize listeners continue positioning the marker and thread as the browser scrolls. No embedded retry delay is introduced.
- In embedded SCORM, completion remains retryable and idempotent. A text-highlight request completes only when the recovered range is close to the vertical centre of its nearest nested scrollport and the marker and thread are visible. A visible target near the bottom is not complete: another attempt recentres it.
- For embedded visual pins, the existing visibility contract remains unchanged because their element-based scrolling already uses the relevant embedded container.
- Direct marker clicks continue toggling threads normally; programmatic retries continue keeping the requested thread open.

The centre tolerance will be small enough to produce the intended middle placement while allowing normal fractional layout and smooth-scroll rounding. The calculation will include the scrollport border through `clientTop`.

## Tests

Regression coverage will prove:

1. Top-level Moodle `takeToContext` acknowledges immediately after issuing its exact scroll, without waiting for a second call.
2. An embedded Rise text range that is visible near the bottom remains retryable and receives a centre-scroll request.
3. The same embedded request acknowledges only once the range is centred and its marker/thread are visible.
4. Existing exact-range, clipping, idempotency, interaction, and worker retry tests remain green.

## Release

The verified browser-loadable release will be version 0.5.33 in the existing `Beta Testing App-pilot-builds` release folder.
