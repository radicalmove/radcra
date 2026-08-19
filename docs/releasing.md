# Sphere release process

Sphere publishes two distinct artifacts for version `0.6.0` and later:

- `sphere-web-store-v<version>.zip` — root-level `manifest.json` package uploaded as a private Chrome Web Store item.
- `moodle-review-extension-v<version>-chrome-edge.zip` — nested `moodle-review-extension/` pilot archive for Chrome/Edge Developer mode.

The public homepage is https://radicalmove.github.io/sphere/. Privacy is https://radicalmove.github.io/sphere/privacy/, support is https://radicalmove.github.io/sphere/support/, and update metadata is https://radicalmove.github.io/sphere/latest.json. Public contact: rcadavies@gmail.com.

## Local release

Use the existing external-delivery process from a clean checkout. Keep `PRIVATE_KEY_PATH` outside the repository and provide the approved `REVIEW_SERVICE_ORIGIN`:

```sh
PRIVATE_KEY_PATH=/secure/path/sphere-production.pem \
REVIEW_SERVICE_ORIGIN=https://review.example.invalid \
deploy/scripts/release-pilot-extension.sh
```

The script runs extension/server/package gates, derives the public key, creates both package shapes, validates checksums, and writes immutable delivery output outside the repository. Never commit `extension/dist`, a PEM, or generated release metadata.

## Tagged GitHub release

1. Confirm a clean source commit, version `0.6.0` in the extension package, and the approved production public-key identity.
2. Configure repository secret `EXTENSION_PRIVATE_KEY_PEM` and variable `REVIEW_SERVICE_ORIGIN`; neither is uploaded or echoed.
3. Create and push an annotated `vX.Y.Z` tag only after release approval. CI uses the immutable checked-out tag commit as `BUILD_COMMIT`, installs pinned dependencies, and runs extension/typecheck/server/deployment/store/release-artifact/public-site tests.
4. CI stores pilot and Web Store outputs under `$RUNNER_TEMP`, removes the temporary mode-600 key using an unconditional trap, and uploads ZIPs, checksums, release notes, and metadata to the technical release record.
5. The independent Pages workflow requires masked `SPHERE_PAGES_REPOSITORY_TOKEN`, stages committed `site/` under `sphere/`, stages only the four compatibility fixtures under `radcra/`, and pushes those paths to `radicalmove/radicalmove.github.io` main.

The `latest.json` schema is exactly:

```json
{
  "schema_version": 1,
  "version": "0.6.0",
  "release_url": "https://github.com/radicalmove/radcra/releases/tag/v0.6.0",
  "download_url": "https://radicalmove.github.io/sphere/",
  "published_at": "2026-08-20T00:00:00Z"
}
```

The `/radcra/latest.json` compatibility response retains this schema and points downloads to Sphere. It contains release metadata only; the `/radcra/` compatibility pages contain only migration links.

## Post-publication checks

In a clean Chrome profile, verify the first-run disclosure, comment author prefixes, chevron minimise/expand states, Moodle markers, optional Rise/SCORM access, sign-out, and metadata-only update status. Web Store installs receive browser-managed updates; unpacked pilots are manually replaced and reloaded. Stop if the Store identity, public key, or any of the six unauthenticated URL contracts differ from the approved release.
