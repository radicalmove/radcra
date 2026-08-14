# RADCRA private-beta reviewer guide

This is a private beta for authorised course reviewers. Install the uploaded root-level Web Store ZIP as a private item and add trusted testers in the Developer Dashboard. Sign in with reviewer credentials supplied out-of-band; never place test credentials in this repository.

The first upload must preserve the accepted pilot public key and therefore the existing `chrome://extensions` ID. Verify that ID matches the dashboard Item ID and that the server's exact extension redirect URI is unchanged. If the dashboard rejects the key, stop and follow the documented migration path rather than shipping a new identity.

Reviewers can inspect the first-run privacy disclosure, accept or decline it, sign in, open a Moodle course, add a comment, and use Help → Check for updates. The updater reads only `latest.json`; it never executes downloaded content.

## Test path

Use an invited Moodle account on the configured `https://my.uconline.ac.nz/*` test URL. Open a normal Moodle page and verify the disclosure, sign-in, current-page comments, text highlight, area marker, reply, resolve/reopen, and Previous/Next navigation. Open a Moodle SCORM player and confirm the Rise/Articulate embedded frame is ready before testing a tab or process-step comment; the optional embedded-origin permission is requested only when needed. Use Sign out to clear local session/device credentials.

Report failures with the course/page URL, extension version, and a minimal reproduction through the support issue tracker. Do not attach access tokens, private keys, or credentials.
