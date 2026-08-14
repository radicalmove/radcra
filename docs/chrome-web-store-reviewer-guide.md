# RADCRA private-beta reviewer guide

This is a private beta for authorised course reviewers. Install the uploaded root-level Web Store ZIP as a private item and add trusted testers in the Developer Dashboard. Sign in with reviewer credentials supplied out-of-band; never place test credentials in this repository.

The first upload must preserve the accepted pilot public key and therefore the existing `chrome://extensions` ID. Verify that ID matches the dashboard Item ID and that the server's exact extension redirect URI is unchanged. If the dashboard rejects the key, stop and follow the documented migration path rather than shipping a new identity.

Reviewers can inspect the first-run privacy disclosure, accept or decline it, sign in, open a Moodle course, add a comment, and use Help → Check for updates. The updater reads only `latest.json`; it never executes downloaded content.
