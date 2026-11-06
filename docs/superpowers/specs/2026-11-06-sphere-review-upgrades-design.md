# Sphere course review upgrades

Build on Sphere 0.6.0 in its existing worktree. Preserve existing pilot builds and use a separate test build. Keep course and comment visibility rules in force for markers, history, exports, and attachments.

## Quiz preview evidence

On confirmed Moodle quiz previews, save the comment with a stable quiz link, question identifier or visible number, and relevant question context when available. Do not rely on temporary attempt URLs or assume that another reviewer can open the original attempt. Never capture learner attempts.

Attach a screenshot automatically when saving a preview comment if Chrome has granted access to capture that tab. Use the Sphere toolbar action to grant temporary access rather than requesting access to every site. Explain the automatic capture in the preview UI and allow it to be disabled. Capture the quiz without the composer or other Sphere UI. Reject captures if the tab or document changed, validate the image, and upload it through the existing authorized attachment flow. If capture or upload fails, preserve the comment and its question context, report that the image was not attached, and avoid duplicate saves.

## Anchors and markers

Preserve the original quote as evidence. Try the exact match first, then recover an edited passage only when surrounding context uniquely identifies it. Show the original and the current text separately and label the current text as unavailable when the match is uncertain. For lost quotes, use a labelled approximate marker only at a reliable surviving location; otherwise keep the thread accessible in the review list. Resolved comments follow the same rules and are visible when the resolved view is enabled. Match nearby markers to cards using numbered badges and focus or hover emphasis, without relying on colour alone.

## Review workspace and controls

Show an unresolved count for Whole course or Current page; switching to the Resolved list does not change that count. Add a full-screen course review view with author, creation date, status history (including actor and date), original quote, current text where verified, and source links. Build on existing status events rather than inferring who resolved older records. Include a personal change checklist that does not mutate shared comment status. Export authorized rows as CSV and JSON; protect CSV cells from spreadsheet formula execution.

Provide Pause/Resume from the Sphere toolbar menu. Pausing hides the overlay and suspends Sphere activity on the page; the toolbar remains available to resume.

## Acceptance checks

Verify in a local Chrome test build: preview capture after granting access, comment save without access, inactive-tab and learner-attempt rejection, overlapping markers, changed and deleted quotes, resolved visibility, course/page counts, history and export visibility, and pause/resume. Use fixtures or a designated Moodle test course for writes.
