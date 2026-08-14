# RADCRA private-beta reviewer guide

This is a private beta for approved reviewers. Test accounts, invitation codes, and Moodle URLs are supplied out-of-band and must never be committed to this repository.

## Access supplied to a reviewer

The operator supplies a test Moodle URL matching the configured pattern (for example, `https://my.uconline.ac.nz/course/view.php?id=<numeric-course-id>`), a course invitation, and a reviewer account. If the course includes a Rise/SCORM package, the operator also approves the exact package host pattern; Chrome will ask for that optional permission only when the package is opened.

## Fresh-install test

1. Install the private Web Store item in a clean Chrome profile, or load the nested `moodle-review-extension/` folder from the pilot ZIP in Developer mode.
2. Open the supplied Moodle course URL. Confirm that ordinary Moodle browsing still works while the RADCRA disclosure is displayed.
3. Read the data-use disclosure and privacy policy. Choose **Continue** to acknowledge the current policy version, or choose **Decline** and confirm that the reviewer remains signed out and no review request is submitted.
4. Sign in with the supplied pilot account. Confirm the overlay identifies the reviewer and the course.
5. Select a sentence and create a text highlight comment. Add an area marker on a non-selectable region and confirm that both markers show their course/page context.
6. Open the Comments panel, select the new thread, and use its navigation control. Confirm the target Moodle page/SCORM activity opens at the saved context.
7. If the course contains an approved embedded activity, open it and grant the exact optional host permission. Add a comment in the activity and verify that denying optional access leaves the parent-page marker path available.
8. Use Help → **Check for updates**. Confirm the result is status/link text only; no ZIP is fetched or executed by the extension. Web Store items update through Chrome, while an unpacked pilot requires a manual folder replacement and Reload.
9. Sign out or choose **Sign out / switch user**. Confirm active session material is cleared and the reviewer can browse Moodle without a connected review session.

## Reporting a finding

Record the build version, browser, Moodle URL pattern (not credentials), page/activity context, expected result, actual result, and a screenshot only when the test account permits it. Report issues at https://github.com/radicalmove/Beta-testing-app/issues. Do not paste access tokens, invitation codes, private URLs, or real student data into an issue.
