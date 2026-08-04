# Articulate Connected Packages Support Design

## Context

Articulate Rise Connected Packages differ from ordinary exported SCORM packages. The uploaded ZIP contains a same-origin Moodle launcher (`indexAPI.html`), while the actual course is hosted by Articulate in a nested iframe. The supplied representative package declares and loads the exact origin `https://packages.articulateusercontent.com`.

RADCRA already supports permission-gated review workers in cross-origin SCORM frames, but the 0.5.28 pilot build intentionally declares no optional external frame patterns. Chrome therefore prevents the extension from entering the Connected Package iframe. The Moodle toolbar may remain visible, but text highlighting, visual markers, contextual threads, and embedded navigation cannot operate in the hosted course document.

Articulate currently describes Connected Packages as a Labs feature whose behaviour may change. Support must therefore remain narrowly scoped, observable, and easy to revise.

## Goals

- Support review markers, text highlighting, comments, and contextual navigation inside the supplied class of Rise Connected Packages.
- Request access only when a reviewer opens a package that uses the reviewed Articulate host.
- Preserve the existing single Moodle toolbar and elected embedded-worker architecture.
- Prevent Connected Package launcher credentials from entering comment page identities, locators, logs, or API payloads.
- Leave ordinary same-origin SCORM packages unchanged.
- Publish the change as pilot extension 0.5.29 without altering 0.5.28.

## Non-goals

- Do not request broad access to `*.articulateusercontent.com`, all Articulate sites, or all HTTPS pages.
- Do not modify, unpack, proxy, or republish Articulate course content.
- Do not guarantee that markers survive substantive remote course edits. Existing anchor recovery remains best-effort when the author moves or rewrites content.
- Do not add support for unrelated Storyline, Review 360, Quick Share, or future Connected Package hosts without separate observed evidence.

## Considered approaches

### 1. Exact optional host permission — selected

Add `https://packages.articulateusercontent.com/*` to the reviewed pilot optional-frame configuration. The top Moodle frame detects the inaccessible iframe and exposes **Allow SCORM review access**. A direct user click requests the exact Chrome host permission, registers the existing persistent optional content script, and injects the worker into already loaded matching frames. If immediate injection is unavailable, the existing reload-required state is shown.

This preserves least privilege, requires an explicit reviewer action, and reuses security boundaries that already have unit coverage.

### 2. Mandatory host permission

Adding the Articulate host to static `host_permissions` would remove the reviewer prompt, but every installation would receive access even if it never uses Connected Packages. This is unnecessary and makes the permission change less transparent.

### 3. Rewrite or proxy the package

Changing `indexAPI.html`, proxying Articulate content through Moodle, or downloading remote assets would couple RADCRA to Articulate's private runtime, create update and licensing risk, and undermine the purpose of Connected Packages. This approach is rejected.

## Architecture and data flow

1. Moodle loads its local SCORM launcher under `https://my.uconline.ac.nz`.
2. The launcher creates a visible iframe whose source origin is `https://packages.articulateusercontent.com`.
3. The top-frame RADCRA controller recursively traverses accessible same-origin iframe documents. It reaches the Moodle-hosted launcher document, then observes the launcher’s inaccessible Articulate child iframe origin without reading that cross-origin document. Traversal is cycle-safe, visits each accessible document at most once, and reports only inaccessible descendant origins.
4. Because the origin matches the build-declared optional pattern and is not yet granted, the toolbar enters `permission-required` and shows **Allow SCORM review access**.
5. The reviewer clicks the action. The background worker accepts the request only from frame zero on the configured Moodle origin and calls `chrome.permissions.request` in the user-gesture stack for the exact pattern.
6. On approval, the background worker reconciles the persistent optional content-script registration and attempts immediate all-frame injection. The current Connected Package document joins the existing frame election and becomes the embedded review worker.
7. Anchor capture and comment creation continue through the existing one-use, course-bound embedded capability. The Moodle top frame remains the only visible toolbar.
8. Permission denial returns to the permission-required state. Injection failure produces the existing reload-required state. Revocation removes the dynamic script and invalidates embedded workers and pending capabilities.

No server API or database change is required.

## Credential and identity handling

The supplied launch iframe includes a temporary token in its initial URL fragment before posting to Articulate's `content.html`. URL fragments are not sent in HTTP requests, but extension code can read them. RADCRA must never persist such a token.

- Embedded comment `page_url` must continue replacing the runtime hash with RADCRA's derived page label.
- For locator derivation, a fragment is launcher-only when `new URLSearchParams(url.hash.slice(1)).has("token")` is true. In that case the entire fragment is discarded and the locator falls back to the URL pathname plus query string. Ordinary Rise route hashes such as `#/lessons/...` are preserved unchanged. The synthetic test token may use any value, but neither its `token` key nor value may appear in an emitted locator.
- Tests must use synthetic token values and must assert that neither the token key nor value appears in the emitted page identity, locator, or captured anchor event.
- Course-content route/hash locators used for ordinary Rise navigation remain supported.

## Configuration and release

- Replace the intentionally empty pilot optional-frame configuration with the exact reviewed pattern `https://packages.articulateusercontent.com/*` and an explanatory comment citing the representative Connected Package evidence.
- Keep `build-pilot-extension.sh` and the release script's exact-configuration enforcement unchanged.
- Bump canonical extension versions and version assertions from 0.5.28 to 0.5.29.
- Build with the existing Cloudflare service origin and private extension key.
- Publish a new immutable `moodle-review-extension-v0.5.29-chrome-edge.zip` plus the usual unzipped/current aliases. Retain the 0.5.28 artifact.

## Testing

Test-first coverage will establish:

- the reviewed production configuration generates an optional host permission for only `https://packages.articulateusercontent.com/*`;
- a representative two-level frame tree—top Moodle document, accessible same-origin `indexAPI.html` launcher, then inaccessible `packages.articulateusercontent.com` child—enters permission-required state and uses the existing exact-origin permission request;
- recursive origin discovery is cycle-safe, ignores accessible documents as permission candidates, and does not broaden the approved host;
- permission grant registers/injects the worker and denial/revocation remain safe;
- a synthetic Connected Package launcher token is absent from page identities, embedded locators, anchor events, and API-bound comment payloads;
- ordinary same-origin SCORM and existing cross-origin authorization tests remain unchanged;
- production manifest, classic content-script, typecheck, extension suite, browser layout checks, server suite, and deployment package suite pass before release;
- release verification records the existing 0.5.28 artifact checksum before publishing, confirms 0.5.29 is a distinct immutable artifact, and confirms the 0.5.28 artifact and checksum are unchanged afterward.

The final manual check uses a Moodle activity created from the supplied Connected Package: open it with 0.5.29, grant the one-time permission, reload only if requested, create a temporary marker and text comment, confirm both reappear, then delete the temporary test comments.

## Operational caveats

- The reviewer's network must be able to reach Articulate's package host.
- Managed Chrome policy must permit the user to grant this optional host permission.
- If Articulate changes the hosting origin or Connected Package structure, RADCRA will fail closed and require a reviewed configuration update rather than broadening access automatically.
- Remote course updates can invalidate text and DOM anchors when content changes materially; this is an inherent limitation of reviewing mutable hosted content and should be included in pilot guidance.
