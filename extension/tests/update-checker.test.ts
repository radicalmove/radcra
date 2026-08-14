import assert from "node:assert/strict";
import test from "node:test";

import { DOWNLOAD_PAGE_URL, UPDATE_CACHE_KEY, UPDATE_CHECK_INTERVAL_MS, UPDATE_METADATA_URL, UpdateChecker, compareSemVer, handleUpdateCheckMessage, parseUpdateMetadata, type UpdateStorage, validateCheckForUpdateMessage } from "../src/update-checker.ts";

class Storage implements UpdateStorage {
  values: Record<string, unknown> = {};
  async get(key: string) { return { [key]: this.values[key] }; }
  async set(value: Record<string, unknown>) { Object.assign(this.values, structuredClone(value)); }
}

const metadata = (version = "0.5.36") => ({ schema_version: 1, version, release_url: "https://github.com/radicalmove/Beta-testing-app/releases/tag/v0.5.36", download_url: DOWNLOAD_PAGE_URL, published_at: "2026-08-14T00:00:00.000Z" });

test("strictly validates update metadata and HTTPS links", () => {
  assert.deepEqual(parseUpdateMetadata(metadata()), metadata());
  for (const [key, value] of [["schema_version", 2], ["version", "0.5"], ["release_url", "http://github.com/a"], ["download_url", "https://example.com/a with space"], ["published_at", "not a date"]] as const) {
    const invalid = metadata(); (invalid as Record<string, unknown>)[key] = value;
    assert.throws(() => parseUpdateMetadata(invalid), /Invalid update metadata/);
  }
  assert.throws(() => parseUpdateMetadata({ ...metadata(), extra: true }), /Invalid update metadata/);
});

test("update requests accept only the optional force flag", () => {
  assert.deepEqual(validateCheckForUpdateMessage({ type: "CHECK_FOR_UPDATE" }), { force: false });
  assert.deepEqual(validateCheckForUpdateMessage({ type: "CHECK_FOR_UPDATE", force: true }), { force: true });
  for (const message of [{ type: "CHECK_FOR_UPDATE", force: "yes" }, { type: "CHECK_FOR_UPDATE", extra: true }, { type: "OTHER" }, null]) {
    assert.throws(() => validateCheckForUpdateMessage(message), /Invalid CHECK_FOR_UPDATE message/);
  }
});

test("compares semantic versions including prereleases", () => {
  assert.equal(compareSemVer("0.5.10", "0.5.9"), 1);
  assert.equal(compareSemVer("1.0.0-alpha", "1.0.0-alpha.1"), -1);
  assert.equal(compareSemVer("1.0.0", "1.0.0-rc.1"), 1);
  assert.equal(compareSemVer("1.0.0", "1.0.0"), 0);
  assert.throws(() => compareSemVer("0.5", "0.5.1"), /Invalid semantic version/);
});

test("returns update available and never downloads the release asset", async () => {
  const storage = new Storage(); const requests: Array<[string, RequestInit | undefined]> = [];
  const checker = new UpdateChecker(storage, "0.5.35", async (url, init) => { requests.push([url, init]); return { ok: true, status: 200, json: async () => metadata() }; });
  const result = await checker.check();
  assert.equal(result.status, "update-available");
  assert.equal(result.metadata?.version, "0.5.36");
  assert.equal(requests.length, 1);
  assert.equal(requests[0]?.[0], UPDATE_METADATA_URL);
  assert.equal(requests[0]?.[1]?.credentials, "omit");
  assert.deepEqual(Object.keys(storage.values), [UPDATE_CACHE_KEY]);
});

test("suppresses repeated checks for 24 hours and allows a forced retry after failure", async () => {
  const storage = new Storage(); let now = 1_000_000; let calls = 0; let fail = true;
  const checker = new UpdateChecker(storage, "0.5.35", async () => { calls += 1; if (fail) throw new Error("offline"); return { ok: true, status: 200, json: async () => metadata() }; }, () => now);
  assert.equal((await checker.check()).status, "retryable");
  assert.equal((await checker.check()).status, "retryable");
  assert.equal(calls, 1);
  fail = false;
  assert.equal((await checker.check({ force: true })).status, "update-available");
  assert.equal(calls, 2);
  now += UPDATE_CHECK_INTERVAL_MS;
  assert.equal((await checker.check()).status, "update-available");
  assert.equal(calls, 3);
});

test("rejects downgrade metadata as retryable rather than reporting up to date", async () => {
  const storage = new Storage();
  const checker = new UpdateChecker(storage, "0.5.35", async () => ({ ok: true, status: 200, json: async () => metadata("0.5.34") }));
  const result = await checker.check();
  assert.equal(result.status, "retryable");
  assert.equal(result.metadata, undefined);
});

test("the background update handler authorizes frame zero and delegates only metadata checks", async () => {
  const calls: Array<{ force: boolean }> = [];
  const result = await handleUpdateCheckMessage({ type: "CHECK_FOR_UPDATE", force: true }, { id: "extension", frameId: 0, url: "https://moodle.example/course/view.php?id=1" }, {
    extensionId: "extension",
    authorize: async () => true,
    check: async (force) => { calls.push({ force }); return { status: "up-to-date", current_version: "0.5.35", checked_at: 1 }; },
  });
  assert.equal(result.status, "up-to-date");
  assert.deepEqual(calls, [{ force: true }]);
  await assert.rejects(() => handleUpdateCheckMessage({ type: "CHECK_FOR_UPDATE" }, { id: "other", frameId: 0 }, { extensionId: "extension", authorize: async () => true, check: async () => ({ status: "up-to-date", current_version: "0.5.35", checked_at: 1 }) }), /Unauthorized/);
  await assert.rejects(() => handleUpdateCheckMessage({ type: "CHECK_FOR_UPDATE" }, { id: "extension", frameId: 2 }, { extensionId: "extension", authorize: async () => true, check: async () => ({ status: "up-to-date", current_version: "0.5.35", checked_at: 1 }) }), /Unauthorized/);
});
