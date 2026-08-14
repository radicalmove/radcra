# RADCRA — Course Review (BETA) privacy policy

**Effective date:** 14 August 2026  
**Policy version:** 2026-08-14  
**Public copy:** https://radicalmove.github.io/Beta-testing-app/privacy/

RADCRA is a private beta Chrome extension for authorised course reviewers. The data controller for this pilot is Richard Davies (University of Canterbury), who can be contacted at **richard.davies@canterbury.ac.nz**. For support or data questions, use the project issue tracker: https://github.com/radicalmove/Beta-testing-app/issues.

## Data the extension handles

- Authentication and reviewer-session information, including short-lived access tokens, device/reconnect credentials, reviewer name, email, role, and approval state.
- Moodle and course information: course, activity, page and SCORM URLs, identifiers, titles, and current page location.
- Reviewer-created content: selected text, visual anchors, comments, replies, status changes, timestamps, and optional screenshots or attachments.
- Operational diagnostics needed to keep the pilot reliable, such as browser/build version, navigation state, and error logs.

The extension stores the minimum local state needed to keep a reviewer signed in, restore pending review access, remember panel preferences, and remember the current policy acknowledgement. The acknowledgement contains only the policy version; it contains no credentials or course content.

## Why it is used

This information is used to authenticate an authorised reviewer, connect the reviewer to the selected course, display and navigate review comments, save reviewer feedback, reconcile status changes, and diagnose or improve the beta extension. Optional screenshots and attachments are uploaded only when the reviewer explicitly requests them.

## Sharing and security

Data is sent only to the configured RADCRA review service and the Moodle site that the reviewer is already using. It is not sold, used for advertising, or shared with data brokers. Access is restricted by course membership and reviewer permissions. Network traffic to the review service uses HTTPS; tokens are kept in Chrome session storage where possible and are never placed in public update metadata or release packages. The extension does not execute remote code.

## Retention and deletion

Review comments and related course data remain in the review service until the course owner or an authorised reviewer deletes them under the service’s controls. A reviewer can sign out to remove local session and device credentials. Declining the policy leaves the reviewer signed out and prevents course data access. To request deletion or ask about retention, contact Richard Davies or use the support issue tracker above.

## Chrome Web Store Limited Use disclosure

RADCRA’s use of data complies with the Chrome Web Store User Data Policy, including the **Limited Use** requirements. The extension uses user data only to provide or improve the extension’s single purpose—course review—and does not transfer, sell, or use that data for unrelated purposes such as advertising or creditworthiness. Human access is limited to the people who need it to operate, support, or improve the authorised beta review service.

This policy may change when the beta’s data practices change. A new policy version requires a fresh acknowledgement before the extension can access course or review data.
