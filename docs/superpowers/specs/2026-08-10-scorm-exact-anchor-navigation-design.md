# SCORM Exact Anchor Navigation Design

## Goal

Make one click on a SCORM comment navigate to its exact highlighted text and leave its comment thread open and visible, including immediately after changing Rise lessons.

## Evidence and root cause

Live tracing on SOWK610-SOWK303-26S2 reproduced the reported sequence. The first click changed to 1.1.3, scrolled while Rise was still laying out the lesson, then acknowledged success before Rise reset `.page-wrap` near the top. The open thread remained hidden. A second click called `scrollIntoView()` on the recovered range's large common ancestor, centring much of the lesson and overshooting the quote; because the hidden thread was already active, that call also toggled it closed.

## Design

- For text highlights, calculate the recovered `Range` rectangle and scroll its nearest scrollable ancestor by the exact delta needed to centre that rectangle. Do not scroll the range's common ancestor element.
- Make programmatic `takeToContext` idempotent: if the requested thread is already active, keep it open.
- Return success only when the requested marker and thread are actually visible in the viewport. An unresolved or offscreen result remains retryable through the existing embedded-navigation state machine.
- Keep existing route selection, interaction restoration, backoff, and expiry behaviour unchanged.
- Release as 0.5.32.

## Verification

- Renderer regression tests for exact nested-scroller range deltas, idempotent repeated attempts, and false-until-visible completion.
- SCORM worker/navigation regression proving the first offscreen attempt is not acknowledged as complete and a later visible attempt is.
- Full extension tests, typecheck, production build, immutable release identity, and checksums.

