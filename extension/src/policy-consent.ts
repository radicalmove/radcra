import { REVIEWER_DEVICE_PREFIX, REVIEWER_SESSION_PREFIX } from "./reviewer-course-access.ts";

export const POLICY_VERSION = "2026-08-14";
export const POLICY_STATE_KEY = "policyAcknowledgement";

type ReadStorage = { get(key: string): Promise<Record<string, unknown>> };
type WriteStorage = { set(value: Record<string, unknown>): Promise<void> };
type RemoveStorage = { remove(keys: string | string[]): Promise<void> };
type LocalAccessStorage = RemoveStorage & { get?(key: string | null): Promise<Record<string, unknown>> };

export type PolicyState = { acknowledged: boolean; version?: string };
export type AccessStorage = { session: LocalAccessStorage; local: LocalAccessStorage };

function policyRecord(value: unknown): { version: string } | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const record = value as Record<string, unknown>;
  if (Object.keys(record).length !== 1 || typeof record.version !== "string") return undefined;
  return { version: record.version };
}

export async function readPolicyState(storage: ReadStorage): Promise<PolicyState> {
  try {
    const record = policyRecord((await storage.get(POLICY_STATE_KEY))[POLICY_STATE_KEY]);
    if (!record) return { acknowledged: false, version: undefined };
    return { acknowledged: record.version === POLICY_VERSION, version: record.version };
  } catch {
    return { acknowledged: false, version: undefined };
  }
}

export async function acknowledgePolicy(storage: WriteStorage): Promise<boolean> {
  try {
    await storage.set({ [POLICY_STATE_KEY]: { version: POLICY_VERSION } });
    return true;
  } catch {
    return false;
  }
}

export async function requiresPolicyAcknowledgement(storage: ReadStorage): Promise<boolean> {
  return !(await readPolicyState(storage)).acknowledged;
}

export async function clearAccessState({ session, local }: AccessStorage): Promise<void> {
  const keys = async (storage: LocalAccessStorage, prefixes: string[]) => {
    try { return Object.keys(await storage.get?.(null) ?? {}).filter((key) => prefixes.some((prefix) => key.startsWith(prefix))); }
    catch { return []; }
  };
  const [sessionKeys, localKeys] = await Promise.all([keys(session, [REVIEWER_SESSION_PREFIX]), keys(local, ["pending-review-access:", REVIEWER_DEVICE_PREFIX])]);
  await Promise.all([
    session.remove(["apiToken", "expiresAt", ...sessionKeys]).catch(() => undefined),
    local.remove(["courseTeamSession", "deviceCredential", "deviceCourseHandle", "reviewerEmail", "reviewerMembershipId", ...localKeys]).catch(() => undefined),
  ]);
}
