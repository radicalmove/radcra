# Sphere 0.6.16 — LEARN staging

This is an unpacked development build, not the Store package. It uses a separate extension identity and a disposable local service. It must not replace a UCO pilot installation or be distributed as a production build.

## Review access

1. On [LEARN course 3598](https://learn.canterbury.ac.nz/course/view.php?id=3598), open **Sign in → Request access**. Enter a dummy name, email address, and requested role. No password is needed.
2. The staging mailbox captures an admin notice. The admin selects the actual role and approves the request. The mailbox then captures the reviewer's confirmation link, assigned role and Moodle course URL.
3. Open the confirmation in the requesting Chrome profile, return to the course, and choose **Check access**. Chrome remembers that course's access. A different Chrome profile needs an email link but no repeat admin approval.

For this test, emails are captured by the local fixture; no SMTP is used. In-memory requests and comments disappear when it restarts.

## Test results

- 284 backend tests passed. 538 extension tests passed and 9 were skipped; TypeScript checking passed.
- A disposable Chrome profile passed request, approval, confirmation and reconnect for two hosts with the same Moodle course number. A second clean profile passed email-only sign-in and confirmation without another admin notice.
- In signed-in Chrome on the actual LEARN test course, a dummy reviewer connected as an SME, saved a local comment marker, and saw it after reloading. No Moodle course content was edited.
- CRJU160, the live Sphere service, and the Chrome Web Store submission were untouched. Quiz and SCORM were not part of this live check.

## Local harness

`server/tests/staging_learn_flow.py` uses a loopback-only, in-memory database. The browser regression is `extension/e2e/learn-access-flow.spec.ts`, enabled with `SPHERE_LEARN_FLOW=1` against the TLS loopback fixture on port 48140. The separately packaged LEARN-only extension uses the manual fixture on HTTP loopback port 48141. Captured confirmation paths are served by that same manual fixture; use its loopback origin when testing a captured link. The fixture mailbox and its dummy credentials must never be exposed beyond localhost.
