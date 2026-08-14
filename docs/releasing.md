# RADCRA release process

Use `deploy/scripts/release-pilot-extension.sh` with `PRIVATE_KEY_PATH` outside the repository and `REVIEW_SERVICE_ORIGIN` set. It produces the established nested pilot ZIP plus a separate root-level Web Store ZIP. Verify checksums and confirm no PEM, source map, or private build metadata is present.

Tagged CI uses `EXTENSION_PRIVATE_KEY_PEM` and the `REVIEW_SERVICE_ORIGIN` repository variable, writes a mode-600 temporary PEM, and removes it with a trap. It runs extension, server, deployment, store-package, and public-site tests before publishing assets and deploying Pages metadata.

CI builds with `BUILD_COMMIT=${{ github.sha }}` in an isolated runner directory; it never relies on the developer's `Beta Testing App-pilot-builds` folder. The tagged job publishes the root-level Web Store ZIP, nested pilot ZIP, `SHA256SUMS`, per-package checksums, and release notes, then deploys the generated `latest.json` to Pages.

Public URLs: download https://radicalmove.github.io/Beta-testing-app/, privacy https://radicalmove.github.io/Beta-testing-app/privacy/, metadata https://radicalmove.github.io/Beta-testing-app/latest.json, support https://github.com/radicalmove/Beta-testing-app/issues.

Do not tag or publish a release without explicit release authorization. After private Web Store publication, manually verify the dashboard Item ID, privacy/support URLs, trusted testers, reviewer access, and a later browser-managed update.
