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
- Public update, support and privacy paths move from the `radcra` path to the `sphere` path.
- Build/repository identifiers that are not user-facing may remain stable where changing them risks an avoidable migration. The Chrome extension's existing public key and extension ID must remain unchanged so installed pilot copies remain the same extension.

## Sphere identity assets

Sphere receives a new packaged visual identity, used by the extension icon, toolbar, Store promotional asset, public site and documentation.

- The mark is an original, geometric blue sphere with a restrained course-review speech-bubble cue.
- It uses the Sphere/CUBE-family blue ramp, not the CUBE Necker-cube artwork or wordmark.
- The mark is legible at 16, 48 and 128 pixels and follows the existing Store icon safe-area requirements.
- Store promotional imagery and the genuine Store screenshot use the Sphere identity and release version 0.6.0.
- All assets are local, checked into the project and produced deterministically. No interface asset is fetched remotely at runtime.

## Visual system

The supplied CUBE standards at `/Users/rcd58/OpenAI Projects/design-standards` are the design source of truth.

### Token rules

- Use a pale-blue ground and white cards/inputs.
- Use deep navy/blue inks only: primary `#0C447C`, secondary `#185FA5`, metadata `#4A78A8`.
- Use `#378ADD` as the single primary action colour. Its darker steps are hover/active states.
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

- Add a compact, icon-only, downward-chevron button to the toolbar's top-right.
- The chevron visually indicates collapsing/minimising the comments panel.
- It has no visible text. Its native hover tooltip and accessible name are **"Minimise comments"**.
- It invokes exactly the same panel-toggle action as the existing **Comments** control. Therefore it preserves all existing panel-state, focus and accessibility behaviour.
- The existing Comments control remains the normal, obvious way to reopen the panel.

## Comment-list author treatment

Each comment excerpt in every list view begins with the comment author's first name:

```
Richard "This should be black not white"
```

- The first name is derived from the comment author's display name.
- It is styled with the secondary Sphere blue, distinct from the deep-navy comment excerpt.
- The first-name treatment appears in whole-course, current-page, open and resolved views, including grouped page/SCORM lists.
- The excerpt is still quoted and retains its current truncation, sorting, navigation and keyboard behaviour.
- If a display name is missing or cannot yield a usable first name, omit the author fragment rather than invent a label or break the list.

## Accessibility and interaction requirements

- Every icon-only control has an accurate accessible name and native tooltip.
- Keyboard focus uses the Sphere blue focus treatment; contrast complies with the source standard's documented roles.
- The minimise control synchronises its `aria-expanded` state with the existing Comments control.
- Existing comment navigation, panel state persistence, reduced-motion behaviour, comment filtering and screen-reader announcements remain intact.
- Status presentation is converted from decorative dots to concise text or appropriate tinted state treatment without reducing the existing connection/authentication information.

## Versioning and distribution

- Set the canonical extension version to **0.6.0**.
- Rename public pages, metadata and release material to Sphere and the new `sphere` GitHub Pages path.
- Preserve the extension signing identity and build pipeline. Do not add private key material to the repository or extension package.
- Update Store/package checks, checksums, readiness evidence and release workflow so they validate the Sphere name, assets, links and 0.6.0 version.

## Implementation boundaries

Expected implementation areas:

1. Central Sphere token layer and refactoring of overlay, renderer and marker styles away from hard-coded legacy teal/red/black values.
2. Original Sphere icon/promo asset generator and deterministic output tests.
3. Toolbar markup and panel-toggle wiring for the downward-chevron minimise button.
4. Comment-list rendering for the first-name/excerpt treatment.
5. Product-name and public-path update through manifests, build configuration, public site, Store documents, help/policy copy and release tooling.
6. Version bump and release/readiness evidence updates.

No server data migration, API change, reviewer-permission change or navigation algorithm rewrite is in scope.

## Verification

Before release, verify:

- Unit tests cover first-name extraction/rendering, missing-name fallback, both panel toggle controls, accessible labels and shared expanded state.
- Style tests verify the Sphere token layer is applied to overlay and renderer surfaces rather than relying on legacy values.
- Icon/promo tests verify deterministic output and Chrome Store dimensions/safe area.
- Extension, typecheck, packaging, public-site, Store-readiness and release-artifact suites pass.
- A genuine Chrome session confirms the Sphere toolbar, author-prefixed comment list, minimise chevron, marker, dialog and embedded-content interface work on both Moodle and SCORM/Rise content.
- The production packages, checksums and Store-readiness report identify exactly version 0.6.0 and preserve the accepted extension ID.
