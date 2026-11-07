import assert from "node:assert/strict";
import test from "node:test";
import { clearAccessState } from "../src/policy-consent.ts";
import { ReviewerCourseAccess } from "../src/reviewer-course-access.ts";

function storage(values: Record<string, unknown> = {}) {
  return {
    async get(keys: string | string[] | null) {
      return keys === null ? { ...values } : Object.fromEntries([keys].flat().map((key) => [key, values[key]]));
    },
    async set(next: Record<string, unknown>) { Object.assign(values, next); },
    async remove(keys: string | string[]) { for (const key of [keys].flat()) delete values[key]; },
  };
}
const sessionToken = (apiToken: string) => ({ apiToken, expiresAt: Date.now() + 60_000 });
const trust = async () => undefined;

test("legacy access is renewed only for its saved course and kept alongside a new course", async () => {
  const local = storage({ deviceCourseHandle: "course-a", deviceCredential: "legacy-a" });
  const session = storage();
  const calls: string[][] = [];
  const access = new ReviewerCourseAccess(local, session, async (course, credential) => {
    calls.push([course, credential]);
    return { session: sessionToken("renewed-a"), deviceCredential: "rotated-a" };
  }, trust);
  assert.equal(await access.token("course-b"), undefined);
  await access.save("course-b", sessionToken("token-b"), "device-b");
  assert.deepEqual(await Promise.all([access.token("course-a"), access.token("course-a"), access.token("course-b")]), ["renewed-a", "renewed-a", "token-b"]);
  assert.deepEqual(calls, [["course-a", "legacy-a"]]);
  assert.equal((await local.get("reviewer-device:course-a"))["reviewer-device:course-a"], "rotated-a");
  await access.invalidate("course-a", "renewed-a");
  assert.equal(await access.token("course-b"), "token-b");
});

test("a delayed renewal cannot sign a course back in after access is cleared", async () => {
  const local = storage({ "reviewer-device:course-a": "device-a", "reviewer-device:course-b": "device-b" });
  const session = storage({ "reviewer-session:course-b": sessionToken("token-b") });
  let start!: () => void;
  const started = new Promise<void>((resolve) => { start = resolve; });
  let finish!: () => void;
  const finished = new Promise<void>((resolve) => { finish = resolve; });
  const access = new ReviewerCourseAccess(local, session, async () => {
    start();
    await finished;
    return { session: sessionToken("renewed-a"), deviceCredential: "rotated-a" };
  }, trust);
  const outstanding = access.token("course-a");
  await started;
  await access.reset(() => clearAccessState({ local, session }));
  finish();
  assert.equal(await outstanding, undefined);
  assert.deepEqual(await local.get(null), {});
  assert.deepEqual(await session.get(null), {});
});

test("a late read of an expired session does not rotate the credential twice", async () => {
  const local = storage({ "reviewer-device:course-a": "device-a" });
  const session = storage();
  const originalGet = session.get;
  let release!: () => void;
  const delayed = new Promise<void>((resolve) => { release = resolve; });
  let reads = 0;
  session.get = async (keys) => {
    const snapshot = await originalGet(keys);
    if (++reads === 1) await delayed;
    return snapshot;
  };
  let rotations = 0;
  const access = new ReviewerCourseAccess(local, session, async () => {
    rotations++;
    return { session: sessionToken("renewed-a"), deviceCredential: "rotated-a" };
  }, trust);
  const stale = access.token("course-a");
  assert.equal(await access.token("course-a"), "renewed-a");
  release();
  assert.equal(await stale, "renewed-a");
  assert.equal(rotations, 1);
});

test("opening a tab during sign-in waits for the new session instead of renewing it", async () => {
  const local = storage();
  const session = storage();
  const originalSet = session.set;
  let pause!: () => void;
  const paused = new Promise<void>((resolve) => { pause = resolve; });
  let release!: () => void;
  const delayed = new Promise<void>((resolve) => { release = resolve; });
  session.set = async (value) => { pause(); await delayed; await originalSet(value); };
  let rotations = 0;
  const access = new ReviewerCourseAccess(local, session, async () => { rotations++; return {}; }, trust);
  const saving = access.save("course-a", sessionToken("new-token"), "new-device");
  await paused;
  const opening = access.token("course-a");
  release();
  await saving;
  assert.equal(await opening, "new-token");
  assert.equal(rotations, 0);
});
