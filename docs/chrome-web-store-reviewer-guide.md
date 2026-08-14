# RADCRA private-beta reviewer guide

This is a private beta for approved reviewers. Test accounts, invitation codes, and Moodle URLs are supplied out-of-band and must never be committed to this repository.

## Access supplied to a reviewer

The operator supplies a test Moodle URL matching the configured pattern (for example, `https://my.uconline.ac.nz/course/view.php?id=<numeric-course-id>`), a course invitation, and a reviewer account. If the course includes a Rise/SCORM package, the operator also approves the exact package host pattern; Chrome will ask for that optional permission only when the package is opened.

## Fresh-install test

1. Install the private Web Store item in a clean Chrome profile, or load the nested `moodle-review-extension/` folder from the pilot ZIP in Developer mode.
2. Open the supplied Moodle course URL. Confirm that ordinary Moodle browsing still works while the RADCRA disclosure is displayed.
3. Choose **Decline** first. Assert zero course resolution, authentication or renewal, SCORM registration, comment fetch, or Moodle-page transmission; the reviewer remains signed out.
4. Reopen RADCRA in a new clean profile, read the disclosure and privacy policy, then Choose **Continue**.
5. Sign in with the supplied pilot account. Confirm the overlay identifies the reviewer and the course.
6. Select a sentence and create a text highlight comment. Add an area marker on a non-selectable region and confirm that both markers show their course/page context.
7. Open the Comments panel, select the new thread, and use its navigation control. Confirm the target Moodle page/SCORM activity opens at the saved context.
8. If the course contains an approved embedded activity, open it and grant the exact optional host permission. Add a comment in the activity and verify that denying optional access leaves the parent-page marker path available.
9. Use Help → **Check for updates**. Confirm the result is status/link text only; no ZIP is fetched or executed by the extension. Web Store items update through Chrome, while an unpacked pilot requires a manual folder replacement and Reload.
10. With a safe test setup, verify timeout, HTTP-error, and network-offline responses fail gracefully: existing Moodle browsing remains available, no remote code runs, and Retry/status text is bounded.
11. Sign out or choose **Sign out / switch user**. Confirm active session material is cleared and the reviewer can browse Moodle without a connected review session.

RADCRA handles reviewer name, email, role, and approval status; authentication, session, reconnect, and device credentials; course/page URLs and activity/SCORM identifiers, titles, and current location; comments, replies, statuses, timestamps, selected text, visual anchors, and optional screenshots and attachments submitted only at the reviewer's request; and browser/build, navigation, reliability, and error diagnostics. Authorised course-team members may read course-review content. Service operator staff do not routinely read it and may access specific data only on explicit user request about that data, for security or abuse, or legal obligation. Internal operational or improvement use is limited to aggregated and anonymised data.

The update check reads fixed metadata only from https://radicalmove.github.io/radcra/latest.json. GitHub Pages receives ordinary request metadata: IP address, user agent, request time, and requested path. RADCRA sends it no Moodle content, review content, credentials, or tokens.

## Reporting a finding

Record the build version, browser, Moodle URL pattern (not credentials), page/activity context, expected result, actual result, and a screenshot only when the test account permits it. Use https://radicalmove.github.io/radcra/support/ or rcadavies@gmail.com. Never send credentials, tokens, invitation codes, private course links, real student data, or unnecessary course content.
