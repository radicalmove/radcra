# Sphere private-beta reviewer guide

This is a private beta for approved reviewers. Test accounts, invitation codes, and Moodle URLs are supplied out-of-band and must never be committed to this repository.

## Access supplied to a reviewer

The operator supplies a test Moodle URL matching the configured pattern, a course invitation, and a reviewer account. If the course includes a Rise/SCORM package, the operator also approves the exact package host pattern; Chrome asks for that optional permission only when the package is opened.

## Fresh-install test

1. Install the private Web Store item in a clean Chrome profile, or load the nested `moodle-review-extension/` folder from the pilot ZIP in Developer mode.
2. Open the supplied Moodle course URL. Confirm ordinary Moodle browsing still works while the Sphere disclosure is displayed.
3. Choose **Decline** first. Assert zero course resolution, authentication or renewal, SCORM registration, comment fetch, or Moodle-page transmission; the reviewer remains signed out.
4. Reopen Sphere in a new clean profile, read the disclosure and privacy policy, then choose **Continue**.
5. Sign in with the supplied pilot account. Confirm the overlay identifies the reviewer and course.
6. Select a sentence and create a text highlight comment. Add an area marker and confirm both markers show their context.
7. Open Comments, select a thread, and use its navigation control. Confirm the target opens at the saved context. Verify each visible excerpt starts with the author's first name; inspect the accessible label for the full display name.
8. Verify the top-right chevron says **Minimise comments** when open and **Expand comments** when closed, with matching `aria-expanded` state and keyboard activation.
9. If an approved embedded activity is present, grant its exact optional host permission. Verify that denying optional access leaves the parent-page marker path available.
10. Use Help → **Check for updates**. Confirm the result is status/link text only; no ZIP is fetched or executed. Web Store items update through Chrome, while an unpacked pilot requires manual folder replacement and Reload.
11. Verify timeout, HTTP-error, and offline responses fail gracefully, then sign out and confirm active session material is cleared.

Sphere handles reviewer name, email, role, and approval status; authentication, session, reconnect, and device credentials; course/page URLs and activity/SCORM identifiers, titles, and current location; comments, replies, statuses, timestamps, selected text, visual anchors, and optional screenshots and attachments submitted only at the reviewer's request; and browser/build, navigation, reliability, and error diagnostics. Authorised course-team members may read course-review content. Service operator staff do not routinely read it and may access specific data only on explicit user request about that data, for security or abuse, or legal obligation. Internal operational or improvement use is limited to aggregated and anonymised data.

The update check reads fixed metadata only from https://radicalmove.github.io/sphere/latest.json. GitHub Pages receives ordinary request metadata: IP address, user agent, request time, and requested path. Sphere sends it no Moodle content, review content, credentials, or tokens.

## Reporting a finding

Record the build version, browser, Moodle URL pattern (not credentials), page/activity context, expected result, actual result, and a screenshot only when the test account permits it. Use https://radicalmove.github.io/sphere/support/ or rcadavies@gmail.com. Never send credentials, tokens, invitation codes, private course links, real student data, or unnecessary course content.
