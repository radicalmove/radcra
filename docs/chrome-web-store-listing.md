# Chrome Web Store listing — private beta

Use this copy for the RADCRA private Chrome Web Store item. Do not publish the item publicly or add testers without explicit release approval.

## Listing fields

**Name:** `RADCRA — Course Review (BETA)`

**Short description:** `Review configured Moodle course pages with comments, highlights, and review markers.`

**Detailed description:**

> **THIS EXTENSION IS FOR BETA TESTING.** RADCRA is a browser-level course-review tool for authorised reviewers. On configured Moodle course pages, a reviewer can highlight text, place an area marker, write a comment, reply to a thread, change its status, and navigate back to the exact course context. Approved embedded Rise/SCORM content can be reviewed when the reviewer grants its optional host permission. The extension does not change Moodle content.
>
> RADCRA sends review identity, course/page context, selected text, comments, replies, statuses, and explicitly requested screenshots/attachments to the configured review service so authorised course teams can discuss and resolve feedback. See the [privacy policy](https://radicalmove.github.io/Beta-testing-app/privacy/) before use. Support is available through the [project issue tracker](https://github.com/radicalmove/Beta-testing-app/issues).
>
> Release metadata is read from `https://radicalmove.github.io/Beta-testing-app/latest.json`. That permission is used only to read JSON version metadata; it never reads Moodle page content, downloads code, executes remote code, or replaces the extension. Chrome Web Store installations update through Chrome. Unpacked pilot installations are updated manually by replacing the folder and pressing Reload.

**Single purpose:** Help an authorised reviewer record, discuss, navigate, and resolve contextual feedback on configured Moodle course pages.

**Category suggestion:** Productivity (or Education if the dashboard offers that category).

## Permission justifications

| Permission/host | Justification shown to the reviewer |
| --- | --- |
| `identity` | Starts the approved reviewer sign-in flow and receives a one-time callback; dashboard cookies are not used as API credentials. |
| `storage` | Keeps the short-lived session, trusted reviewer access state, panel preferences, and versioned privacy acknowledgement in the extension-owned storage boundaries. |
| `scripting` | Coordinates the review overlay and exact comment navigation in configured Moodle pages and explicitly approved embedded frames. |
| `tabs` | Reads the active tab URL/title needed to bind a review action to its current Moodle page and to display a safe navigation target. |
| `https://my.uconline.ac.nz/*` (production host) | Runs the overlay only on the configured Moodle course host. No `<all_urls>` permission is used. |
| configured review-service host | Sends authenticated review operations to the service configured for this private beta. The exact origin is supplied during the production build. |
| `https://radicalmove.github.io/*` | Reads only the fixed `latest.json` release metadata endpoint for a user-requested or rate-limited update check. It does not read page content. |
| optional Rise/SCORM match patterns | Requested only after a reviewer opens an approved embedded activity, so unrelated sites do not receive access. |

The extension does not request a private key, `downloads`, or broad web access. It does not execute remotely hosted JavaScript.

## Privacy practices answers

- **Chrome Web Store Limited Use:** RADCRA's use of data complies with the Chrome Web Store User Data Policy, including the Limited Use requirements. User data is used only to provide or improve the single course-review purpose.
- **Does the extension handle user data?** Yes. It handles reviewer identity/email and session material, Moodle/course/page URLs and titles, selected text, comments/replies/status, optional screenshots or attachments, and operational logs.
- **Is the data sold or used for advertising/creditworthiness?** No.
- **Purpose:** The data is used only to provide and support the single course-review purpose. It is sent to the configured review service and the Moodle site already being reviewed.
- **Human access:** Limited to people who need it to operate, support, or improve the authorised beta review service.
- **Privacy policy URL:** https://radicalmove.github.io/Beta-testing-app/privacy/
- **Support URL:** https://github.com/radicalmove/Beta-testing-app/issues

## Private-beta distribution

Upload the root-level `radcra-web-store-v<version>.zip` from a tagged GitHub Release, set distribution to private, and add only approved trusted testers. The package has `manifest.json` at its root. Keep the nested `moodle-review-extension-v<version>-chrome-edge.zip` as the developer fallback; it is not the Web Store upload package.

Before the first submission, compare the dashboard public key with the accepted pilot public key byte-for-byte after canonical base64/DER normalisation. Copy the dashboard Item ID and compare it with the unpacked `chrome://extensions` ID. If the identity differs, stop and follow the documented migration; never silently publish a second identity. Register only the exact `chrome.identity.getRedirectURL()` value with the review service.
