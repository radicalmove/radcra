import assert from "node:assert/strict";
import test from "node:test";
import { showInstalledUpdate } from "../src/installed-update-notice.ts";

test("only an actual Sphere version change stores an update notice and marks the toolbar", async () => {
  const calls: unknown[] = [];
  const hooks = {
    setStorage: async (value: unknown) => { calls.push(value); },
    setBadge: async (text: string) => { calls.push(text); },
  };
  await showInstalledUpdate({ reason: "install" }, "0.6.14", hooks);
  await showInstalledUpdate({ reason: "chrome_update" }, "0.6.14", hooks);
  await showInstalledUpdate({ reason: "update", previousVersion: "0.6.14" }, "0.6.14", hooks);
  assert.deepEqual(calls, []);
  await showInstalledUpdate({ reason: "update", previousVersion: "0.6.13" }, "0.6.14", hooks);
  assert.deepEqual(calls, [{ sphereUpdatedVersion: "0.6.14" }, "NEW"]);
});
