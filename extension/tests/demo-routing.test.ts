import assert from "node:assert/strict";
import test from "node:test";
import { ReviewServiceRouting, scopedStorage } from "../src/demo-routing.ts";

const live = "https://review.example.invalid";
const moodle = "https://moodle.example.invalid";
const demo = "https://demo.example.invalid:10000";
test("only the exact demo Moodle origin uses the isolated service", () => {
  const routing = new ReviewServiceRouting(live, moodle, demo);
  assert.equal(routing.forPage(moodle + "/course/view.php?id=1"), demo);
  assert.equal(routing.forPage("https://moodle.example.invalid:8443/course/view.php?id=1"), live);
  routing.bind("demo-course", moodle + "/course/view.php?id=1");
  assert.equal(routing.forCourse("demo-course"), demo);
  assert.equal(routing.forCourse("live-course"), live);
  assert.throws(() => routing.bind("demo-course", "https://other.example.invalid/"), /conflict/i);
});

test("demo storage never reads or overwrites live credentials", async () => {
  const values: Record<string, unknown> = { deviceCredential: "live-secret" };
  const raw = {
    get: async (keys: string | string[]) => Object.fromEntries([keys].flat().map((key) => [key, values[key]])),
    set: async (next: Record<string, unknown>) => { Object.assign(values, next); },
    remove: async (keys: string | string[]) => { [keys].flat().forEach((key) => delete values[key]); },
  };
  const demoStorage = scopedStorage(raw, "demo:");
  assert.equal((await demoStorage.get("deviceCredential")).deviceCredential, undefined);
  await demoStorage.set({ deviceCredential: "demo-secret" });
  await demoStorage.remove("deviceCredential");
  assert.equal(values.deviceCredential, "live-secret");
});
