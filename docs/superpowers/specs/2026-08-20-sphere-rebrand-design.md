# Sphere rebrand and interface system design

**Status:** Approved for planning  
**Date:** 20 August 2026  
**Release:** 0.6.0

## Purpose

Rename RADCRA to **Sphere** and give the course-review extension a coherent, accessible visual system based on the supplied CUBE design standards. The result must be recognisably Sphere, rather than CUBE: it adopts the standards' colour, typography, spacing, control and accessibility rules, but uses an original sphere-and-comment identity and no CUBE mark.

This is a branding and presentation release. Existing review data, authentication, API contracts, Moodle navigation, SCORM navigation and comment behaviour remain unchanged except where explicitly described below.

## Product identity

- The full extension and Store name is **Sphere - Course Review App (BETA)**.
- The concise name used within the review interface is **Sphere**.
- All user-facing references to RADCRA change to Sphere: extension UI, Store material, public site, privacy and support pages, help text, reviewer material, release notes, screenshots and generated artwork.
- The canonical public Sphere site is `https://radicalmove.github.io/sphere/`, with `privacy/`, `support/` and `latest.json` below that path. Sphere 0.6.0 requests only `https://radicalmove.github.io/sphere/latest.json` for its metadata-only update check and declares `https://radicalmove.github.io/sphere/*` as its update host permission.
- `https://radicalmove.github.io/radcra/latest.json` remains a static compatibility endpoint throughout the 0.6.x pilot line. It advertises 0.6.0 and points to the canonical Sphere release/download page, so installed 0.5.x pilots can discover the rebrand. It serves no Moodle, review, credential or token data. The old public path is otherwise a minimal migration page which points people to Sphere.
- Build/repository identifiers that are not user-facing may remain stable where changing them risks an avoidable migration. The Chrome extension's existing public key and extension ID must remain unchanged so installed pilot copies remain the same extension.

## Sphere identity assets

Sphere receives a new packaged visual identity, used by the extension icon, toolbar, Store promotional asset, public site and documentation.

- The mark is an original, geometric blue sphere with a restrained course-review speech-bubble cue.
- It uses the Sphere/CUBE-family blue ramp, not the CUBE Necker-cube artwork or wordmark.
- The manifest icons are `extension/public/icons/icon16.png`, `icon48.png` and `icon128.png`. They are RGBA PNGs at exactly 16x16, 48x48 and 128x128 pixels; the 128px master artwork has a non-transparent alpha bounding box of 16,16 to 112,112, and the smaller icons derive from that master.
- The generated Store promotional tile is `store-assets/sphere-promo-440x280.png`, exactly 440x280 RGB PNG pixels.
- Icons and the promotional tile are local, checked in, generated deterministically and verified by committed/golden hashes. No interface asset is fetched remotely at runtime.
- The Store screenshot is `store-assets/sphere-screenshot-1280x800.png`, exactly 1280x800 pixels. It is a genuine manual capture of the current Sphere 0.6.0 extension in Chrome, not a generated image. It stays under the existing manual screenshot-review gate, with the same privacy sanitisation procedure used for the current Store image.

## Visual system

The supplied CUBE standards at `/Users/rcd58/OpenAI Projects/design-standards` are the design source of truth.

### Token rules

- Use a pale-blue ground and white cards/inputs.
- Use deep navy/blue inks only: primary `#0C447C`, secondary `#185FA5`, metadata `#4A78A8`.
- Use the CUBE blue ramp for actions. For this extension's 13px button labels, primary buttons use AA-conformant `#185FA5` (`--cube-900`) with white text, `#0C447C` (`--cube-950`) on hover/active, and `#378ADD` (`--cube-800`) for links, selected states and focus emphasis. This satisfies WCAG 2.2 SC 1.4.3 (minimum contrast) for normal-size button text while retaining the standard's one-blue action family.
- Use red only for destructive actions, errors and explicit destructive emphasis.
- Use semantic tints for success, warning and danger states; avoid decorative coloured status lights.
- Use the standard blue hairlines, 4px spacing grid, 6px control radius, 8px container radius, restrained elevation and blue focus ring.
- Use Poppins throughout with the CUBE 13px dense UI default and documented type scale. The current Poppins loading approach must remain local/robust for extension use.

### Scope

The token system applies to all Sphere-owned UI: the floating toolbar and panel, comment list, inline comment cards, markers, selected-text highlight treatment, dialogs, composer, policy disclosure, help, access/authentication states, update UI and embedded SCORM/Rise presentation.

Moodle and embedded course content itself is not recoloured or otherwise restyled.

## Floating panel

The floating panel remains bottom-right and keeps its established responsive dimensions and positioning. Its structure is retained but restyled as a Sphere panel: pale-blue/white surfaces, navy text, blue primary actions and a light card hierarchy.

### Minimise control

- Add a compact, icon-only, downward-chevron button to the toolbar's top-right, associated with the panel by `aria-controls`.
- While the comments panel is open, the chevron points down. Its native hover tooltip and accessible name are **"Minimise comments"** and its `aria-expanded` value is `true`.
- While the panel is closed, the same control points up. Its tooltip and accessible name become **"Expand comments"** and `aria-expanded` becomes `false`.
- It invokes the same single panel-toggle action as the existing **Comments** control, so the controls always synchronise. The existing Comments control remains the normal, obvious way to reopen the panel.
- It has no visible text. At the narrowest supported panel width and at 200% browser zoom, it remains a 32px minimum target without overlapping the version, course title, Comments control or Help control.

## Comment-list author treatment

Each comment excerpt in every list view begins with the comment author's first name:

```
Richard "This should be black not white"
```

- The display-only helper trims the validated `author.display_name`, splits it on one-or-more whitespace characters and returns the first non-empty token. It does not change the existing API validation, which continues to require a nonblank display name.
- It is styled with the secondary Sphere blue, distinct from the deep-navy comment excerpt.
- The first-name treatment appears in whole-course, current-page, open and resolved views, including grouped page/SCORM lists.
- The excerpt is still quoted and retains its current truncation, sorting, navigation and keyboard behaviour.
- If a malformed internal/test value is missing or cannot yield a usable first name, omit the visible author fragment rather than invent a label or break the list. This defensive fallback is tested independently of API validation.
- Each comment button's accessible name includes the full available display name and comment excerpt, so the compact visible first-name treatment does not lose screen-reader context.

## Accessibility and interaction requirements

- Every icon-only control has an accurate accessible name and native tooltip.
- Keyboard focus uses the Sphere blue focus treatment. Normal-size text, including 13px button labels, meets WCAG 2.2 SC 1.4.3 at 4.5:1 or higher; controls meet SC 1.4.11.
- The minimise control synchronises its `aria-expanded` state and `aria-controls` relationship with the existing Comments control. Both open and closed states work by keyboard and retain a visible focus indicator.
- Existing comment navigation, panel state persistence, reduced-motion behaviour, comment filtering and screen-reader announcements remain intact.
- Status presentation is converted from decorative dots to concise text or appropriate tinted state treatment without reducing the existing connection/authentication information.

## Versioning and distribution

- Set the canonical extension version to **0.6.0**.
- Rename public pages, metadata and release material to Sphere and the canonical `https://radicalmove.github.io/sphere/` GitHub Pages path, while publishing the defined `radcra/latest.json` compatibility endpoint for existing pilot update checks.
- Preserve the extension signing identity and build pipeline. Do not add private key material to the repository or extension package.
- Update Store/package checks, checksums, readiness evidence and release workflow so they validate the Sphere name, assets, links and 0.6.0 version.

## Implementation boundaries

Expected implementation areas:

1. Central Sphere token layer and refactoring of overlay, renderer and marker styles away from hard-coded legacy teal/red/black values.
2. Original Sphere icon/promo asset generator and deterministic output tests, plus an explicit manual 1280x800 Sphere screenshot capture/checklist.
3. Toolbar markup and panel-toggle wiring for the downward-chevron minimise button.
4. Comment-list rendering for the first-name/excerpt treatment.
5. Product-name and public-path update through manifests, build configuration, public site, Store documents, help/policy copy and release tooling.
6. Version bump and release/readiness evidence updates.

No server data migration, API change, reviewer-permission change or navigation algorithm rewrite is in scope.

## Verification

Before release, verify:

- Unit tests cover deterministic first-name extraction/rendering, malformed rendering fallback without relaxing API validation, both panel toggle controls, `aria-controls`, accessible labels, shared expanded state, keyboard activation, and narrow/200%-zoom layout.
- Style tests verify the Sphere token layer is applied to overlay and renderer surfaces rather than relying on legacy values.
- Icon/promo tests verify deterministic byte output, committed/golden hashes, exact filenames, exact Chrome Store dimensions, and the documented alpha safe area. Screenshot tests verify its exact filename/dimensions/PNG hygiene and preserve the manual-genuine-capture requirement.
- Extension, typecheck, packaging, public-site, Store-readiness and release-artifact suites pass.
- A genuine Chrome session confirms the Sphere toolbar, author-prefixed comment list, minimise chevron, marker, dialog and embedded-content interface work on both Moodle and SCORM/Rise content.
- The production packages, checksums and Store-readiness report identify exactly version 0.6.0, use canonical Sphere URLs, preserve the accepted extension ID, and leave the legacy RADCRA update endpoint capable of advertising the Sphere release.
