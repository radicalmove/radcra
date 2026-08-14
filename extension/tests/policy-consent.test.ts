import assert from "node:assert/strict";
import test from "node:test";

import { POLICY_STATE_KEY, POLICY_VERSION, acknowledgePolicy, clearAccessState, readPolicyState, requiresPolicyAcknowledgement } from "../src/policy-consent.ts";

class Storage {
  values: Record<string, unknown> = {};
  removed: string[] = [];
  async get(key: string | null) { return key === null ? structuredClone(this.values) : { [key]: structuredClone(this.values[key]) }; }
  async set(value: Record<string, unknown>) { Object.assign(this.values, structuredClone(value)); }
  async remove(keys: string | string[]) {
    for (const key of Array.isArray(keys) ? keys : [keys]) { this.removed.push(key); delete this.values[key]; }
  }
}

test("missing, malformed, and unavailable policy state require acknowledgement", async () => {
  const storage = new Storage();
  assert.deepEqual(await readPolicyState(storage), { acknowledged: false, version: undefined });
  assert.equal(await requiresPolicyAcknowledgement(storage), true);
  storage.values[POLICY_STATE_KEY] = { version: POLICY_VERSION, credential: "must-not-be-accepted" };
  assert.deepEqual(await readPolicyState(storage), { acknowledged: false, version: undefined });
  assert.equal(await requiresPolicyAcknowledgement({ get: async () => { throw new Error("unavailable"); } }), true);
});

test("the exact current version acknowledgement permits review data access without credentials", async () => {
  const storage = new Storage();
  await acknowledgePolicy(storage);
  assert.deepEqual(storage.values[POLICY_STATE_KEY], { version: POLICY_VERSION });
  assert.deepEqual(await readPolicyState(storage), { acknowledged: true, version: POLICY_VERSION });
  assert.equal(await requiresPolicyAcknowledgement(storage), false);
});

test("an acknowledgement for another policy version is invalidated", async () => {
  const storage = new Storage();
  storage.values[POLICY_STATE_KEY] = { version: "obsolete-policy" };
  assert.deepEqual(await readPolicyState(storage), { acknowledged: false, version: "obsolete-policy" });
  assert.equal(await requiresPolicyAcknowledgement(storage), true);
});

test("clearing invalidated access removes session, device, and reviewer keys safely", async () => {
  const session = new Storage(); const local = new Storage();
  Object.assign(session.values, { apiToken: "token", expiresAt: 1 });
  Object.assign(local.values, { courseTeamSession: { apiToken: "token", expiresAt: 1 }, deviceCredential: "device", deviceCourseHandle: "course", reviewerEmail: "reviewer@example.test", reviewerMembershipId: "member", "pending-review-access:123e4567-e89b-42d3-a456-426614174000": { courseHandle: "123e4567-e89b-42d3-a456-426614174000", email: "reviewer@example.test", reconnectCredential: "sensitive-reconnect-code" } });
  await clearAccessState({ session, local });
  assert.deepEqual(session.removed.sort(), ["apiToken", "expiresAt"]);
  assert.deepEqual(local.removed.sort(), ["courseTeamSession", "deviceCourseHandle", "deviceCredential", "pending-review-access:123e4567-e89b-42d3-a456-426614174000", "reviewerEmail", "reviewerMembershipId"]);
  await clearAccessState({ session: { remove: async () => { throw new Error("unavailable"); } }, local: { remove: async () => { throw new Error("unavailable"); } } });
});
