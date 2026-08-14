# RADCRA release process

RADCRA publishes two distinct artifacts for version `0.5.35` and later:

- `radcra-web-store-v<version>.zip` — root-level `manifest.json` package uploaded as a private Chrome Web Store item.
- `moodle-review-extension-v<version>-chrome-edge.zip` — nested `moodle-review-extension/` pilot archive for Chrome/Edge Developer mode.

The public download page is https://radicalmove.github.io/Beta-testing-app/. The privacy policy is https://radicalmove.github.io/Beta-testing-app/privacy/, support is https://github.com/radicalmove/Beta-testing-app/issues, and update metadata is https://radicalmove.github.io/Beta-testing-app/latest.json.

## Local release

Use the existing external-delivery process from a clean checkout. Keep `PRIVATE_KEY_PATH` outside the repository and provide the approved `REVIEW_SERVICE_ORIGIN`:

```sh
PRIVATE_KEY_PATH=/secure/path/radcra-production.pem \
REVIEW_SERVICE_ORIGIN=https://review.example.invalid \
deploy/scripts/release-pilot-extension.sh
```

The script runs the extension/server/package gates, derives the public key, creates both package shapes, validates checksums, and writes immutable delivery output outside the repository. Never commit `extension/dist`, a PEM, or generated release metadata.

## Tagged GitHub release

1. Confirm the clean source commit, version in `extension/package.json` and `extension/package-lock.json`, and the approved production public-key identity.
2. Configure repository secret `EXTENSION_PRIVATE_KEY_PEM` with the existing RSA PEM and repository variable `REVIEW_SERVICE_ORIGIN` with the approved HTTPS origin. These values are consumed only by CI; neither is uploaded or echoed.
3. Create and push an annotated `vX.Y.Z` tag only after release approval. `.github/workflows/release-extension.yml` uses immutable `github.sha` as `BUILD_COMMIT`, installs the pinned build dependencies, runs extension/typecheck/server/deployment/store/public-site tests, and builds with a mode-600 temporary PEM.
4. The key file is created, used to derive the public key, and removed by an unconditional trap in the same build step. CI stores pilot and Web Store outputs under `$RUNNER_TEMP`; it does not call the local external-delivery wrapper or rely on a developer's `Beta Testing App-pilot-builds` directory.
5. CI uploads both ZIPs, their `.sha256` entry, `SHA256SUMS`, and release notes to the GitHub Release. It generates `site/latest.json` with the fixed schema and deploys the complete `site/` directory through GitHub Pages; it does not commit generated metadata.

The `latest.json` schema is exactly:

```json
{
  "schema_version": 1,
  "version": "0.5.35",
  "release_url": "https://github.com/radicalmove/Beta-testing-app/releases/tag/v0.5.35",
  "download_url": "https://github.com/radicalmove/Beta-testing-app/releases/download/v0.5.35/radcra-web-store-v0.5.35.zip",
  "published_at": "2026-08-14T00:00:00Z"
}
```

`published_at` must be an ISO-8601 UTC timestamp. Invalid metadata is treated as no update by the extension.

## Identity and post-publication checks

For the first Web Store draft, compare the dashboard's public key with the accepted unpacked-build key after canonical base64/DER normalisation. Compare the dashboard Item ID with the unpacked `chrome://extensions` ID. Register only the exact `chrome.identity.getRedirectURL()` URI in `EXTENSION_REDIRECT_URIS`. If the identities differ, stop; document and deliberately execute a one-time migration before replacing pilot builds.

In a clean Chrome profile, verify the first-run disclosure before sign-in, Moodle text/area markers, comment navigation, optional Rise/SCORM access, sign-out, and update-check status. The later-version check is a manual dashboard/browser acceptance step: Web Store installs must receive a browser-managed update, while unpacked pilots must be manually replaced and reloaded.
