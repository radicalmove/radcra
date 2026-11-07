import type { SessionToken } from "./api.ts";

export const REVIEWER_DEVICE_PREFIX = "reviewer-device:";
export const REVIEWER_SESSION_PREFIX = "reviewer-session:";

type Storage = {
  get(keys: string | string[]): Promise<Record<string, unknown>>;
  set(values: Record<string, unknown>): Promise<void>;
  remove(keys: string | string[]): Promise<void>;
};
type Renewal = { session?: SessionToken; deviceCredential?: string };
type Renew = (course: string, credential: string) => Promise<Renewal>;
const courseKey = (course: string) => course.toLowerCase();

export function validSession(value: unknown): SessionToken | undefined {
  const session = value as Partial<SessionToken> | undefined;
  return session && typeof session.apiToken === "string" && typeof session.expiresAt === "number" && session.expiresAt > Date.now()
    ? session as SessionToken : undefined;
}

export class ReviewerCourseAccess {
  private readonly renewals = new Map<string, Promise<string | undefined>>();
  private readonly writes = new Map<string, Promise<void>>();
  private clearing?: Promise<void>;
  private epoch = 0;
  private readonly local: Storage;
  private readonly session: Storage;
  private readonly renew: Renew;
  private readonly trustLocal: () => Promise<void>;
  get generation(): number { return this.epoch; }

  constructor(local: Storage, session: Storage, renew: Renew, trustLocal: () => Promise<void>) {
    this.local = local;
    this.session = session;
    this.renew = renew;
    this.trustLocal = trustLocal;
  }

  save(course: string, session: SessionToken, device: string, generation = this.generation): Promise<void> {
    if (this.clearing || generation !== this.generation) return Promise.reject(new Error("Sign-in was reset"));
    const key = courseKey(course);
    const previous = this.writes.get(key);
    const write = (async () => {
      await previous?.catch(() => undefined);
      await this.trustLocal();
      await this.local.set({ [REVIEWER_DEVICE_PREFIX + key]: device });
      await this.session.set({ [REVIEWER_SESSION_PREFIX + key]: session });
    })();
    this.writes.set(key, write);
    void write.finally(() => { if (this.writes.get(key) === write) this.writes.delete(key); }).catch(() => undefined);
    return write;
  }

  async token(course: string): Promise<string | undefined> {
    if (this.clearing) return undefined;
    const key = courseKey(course);
    const generation = this.generation;
    await this.writes.get(key)?.catch(() => undefined);
    const stored = await this.session.get(REVIEWER_SESSION_PREFIX + key);
    if (this.generation !== generation) return undefined;
    const active = validSession(stored[REVIEWER_SESSION_PREFIX + key]);
    if (active) return active.apiToken;
    const pending = this.renewals.get(key);
    if (pending) return pending;
    const operation = this.renewStored(key, generation).finally(() => {
      if (this.renewals.get(key) === operation) this.renewals.delete(key);
    });
    this.renewals.set(key, operation);
    return operation;
  }

  private async renewStored(course: string, generation: number): Promise<string | undefined> {
    const key = REVIEWER_DEVICE_PREFIX + course;
    const sessionKey = REVIEWER_SESSION_PREFIX + course;
    try {
      // A concurrent caller may have completed renewal while this caller's
      // first storage read was still resolving.
      await this.writes.get(course)?.catch(() => undefined);
      const active = validSession((await this.session.get(sessionKey))[sessionKey]);
      if (generation !== this.generation) return undefined;
      if (active) return active.apiToken;
      await this.trustLocal();
      const stored = await this.local.get([key, "deviceCredential", "deviceCourseHandle"]);
      const credential = stored[key] ?? (typeof stored.deviceCourseHandle === "string" && courseKey(stored.deviceCourseHandle) === course ? stored.deviceCredential : undefined);
      if (typeof credential !== "string" || generation !== this.generation) return undefined;
      const renewed = await this.renew(course, credential);
      if (!renewed.session || !renewed.deviceCredential || generation !== this.generation) return undefined;
      // A new sign-in may have replaced the saved credential during renewal.
      const current = (await this.local.get(key))[key];
      if (current !== stored[key]) return validSession((await this.session.get(sessionKey))[sessionKey])?.apiToken;
      await this.save(course, renewed.session, renewed.deviceCredential, generation);
      return generation === this.generation ? renewed.session.apiToken : undefined;
    } catch {
      // Keep the credential if the service or network is temporarily unavailable.
      return undefined;
    }
  }

  async invalidate(course: string, failedToken: string): Promise<void> {
    const key = REVIEWER_SESSION_PREFIX + courseKey(course);
    const stored = (await this.session.get(key))[key] as SessionToken | undefined;
    if (stored?.apiToken === failedToken) await this.session.remove(key);
  }

  reset(clear: () => Promise<void>): Promise<void> {
    if (this.clearing) return this.clearing;
    this.epoch++;
    this.renewals.clear();
    this.clearing = Promise.allSettled(this.writes.values()).then(clear).finally(() => { this.clearing = undefined; });
    return this.clearing;
  }
}
