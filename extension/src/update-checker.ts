/**
 * Safe, metadata-only update checks for the private RADCRA pilot.
 *
 * This module deliberately never downloads an extension package, evaluates
 * remote content, or writes anything except the small metadata cache.
 */

export const UPDATE_METADATA_URL = "https://radicalmove.github.io/radcra/latest.json";
export const DOWNLOAD_PAGE_URL = "https://radicalmove.github.io/radcra/";
export const UPDATE_CACHE_KEY = "radcra.update-check";
export const UPDATE_CHECK_INTERVAL_MS = 24 * 60 * 60 * 1000;

export type UpdateMetadata = {
  schema_version: 1;
  version: string;
  release_url: string;
  download_url: string;
  published_at: string;
};

export type UpdateCheckStatus = "up-to-date" | "update-available" | "retryable";

export type UpdateCheckResult = {
  status: UpdateCheckStatus;
  current_version: string;
  checked_at: number;
  metadata?: UpdateMetadata;
  message?: string;
};

export type UpdateCheckSender = { id?: string; url?: string; frameId?: number };

type CachedResult = {
  checkedAt: number;
  status: UpdateCheckStatus;
  currentVersion: string;
  metadata?: UpdateMetadata;
  message?: string;
};

export type UpdateStorage = {
  get(key: string): Promise<Record<string, unknown>>;
  set(value: Record<string, unknown>): Promise<void>;
};

export type UpdateFetcher = (input: string, init?: RequestInit) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}>;

export function validateCheckForUpdateMessage(message: unknown): { force: boolean } {
  if (!message || typeof message !== "object" || Array.isArray(message)) throw new Error("Invalid CHECK_FOR_UPDATE message");
  const record = message as Record<string, unknown>;
  if (Object.keys(record).some((key) => !["type", "force"].includes(key)) || record.type !== "CHECK_FOR_UPDATE" || (record.force !== undefined && typeof record.force !== "boolean")) {
    throw new Error("Invalid CHECK_FOR_UPDATE message");
  }
  return { force: record.force === true };
}

export async function handleUpdateCheckMessage(
  message: unknown,
  sender: UpdateCheckSender,
  dependencies: {
    extensionId: string;
    authorize(sender: UpdateCheckSender): Promise<boolean>;
    check(force: boolean): Promise<UpdateCheckResult>;
  },
): Promise<UpdateCheckResult> {
  const { force } = validateCheckForUpdateMessage(message);
  if (sender.id !== dependencies.extensionId || sender.frameId !== 0 || !(await dependencies.authorize(sender))) throw new Error("Unauthorized CHECK_FOR_UPDATE sender");
  return dependencies.check(force);
}

const semver = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

function parseVersion(value: unknown): { major: number; minor: number; patch: number; pre: string[] } | undefined {
  if (typeof value !== "string" || value.length > 128) return undefined;
  const match = semver.exec(value);
  if (!match) return undefined;
  const numbers = [match[1], match[2], match[3]].map((item) => Number(item));
  if (numbers.some((item) => !Number.isSafeInteger(item))) return undefined;
  const pre = match[4]?.split(".") ?? [];
  if (pre.some((item) => item.length > 64 || (/^0\d+$/.test(item)))) return undefined;
  return { major: numbers[0]!, minor: numbers[1]!, patch: numbers[2]!, pre };
}

/** Returns -1 when left is older, 0 when equal, and 1 when newer. */
export function compareSemVer(left: string, right: string): -1 | 0 | 1 {
  const a = parseVersion(left);
  const b = parseVersion(right);
  if (!a || !b) throw new Error("Invalid semantic version");
  for (const key of ["major", "minor", "patch"] as const) {
    if (a[key] !== b[key]) return a[key] < b[key] ? -1 : 1;
  }
  if (!a.pre.length && !b.pre.length) return 0;
  if (!a.pre.length) return 1;
  if (!b.pre.length) return -1;
  const length = Math.max(a.pre.length, b.pre.length);
  for (let index = 0; index < length; index += 1) {
    const av = a.pre[index];
    const bv = b.pre[index];
    if (av === undefined) return -1;
    if (bv === undefined) return 1;
    if (av === bv) continue;
    const an = /^\d+$/.test(av);
    const bn = /^\d+$/.test(bv);
    if (an && bn) return Number(av) < Number(bv) ? -1 : 1;
    if (an !== bn) return an ? -1 : 1;
    return av < bv ? -1 : 1;
  }
  return 0;
}

function exactHttpsUrl(value: unknown): value is string {
  if (typeof value !== "string" || value.length > 4096) return false;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" && !parsed.username && !parsed.password && parsed.href === value;
  } catch {
    return false;
  }
}

function isIsoDate(value: unknown): value is string {
  if (typeof value !== "string" || value.length > 128) return false;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

export function parseUpdateMetadata(value: unknown): UpdateMetadata {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid update metadata");
  const record = value as Record<string, unknown>;
  const expected = ["download_url", "published_at", "release_url", "schema_version", "version"];
  if (Object.keys(record).sort().join() !== expected.join() || record.schema_version !== 1
    || !parseVersion(record.version) || !exactHttpsUrl(record.release_url) || !exactHttpsUrl(record.download_url) || !isIsoDate(record.published_at)) {
    throw new Error("Invalid update metadata");
  }
  return {
    schema_version: 1,
    version: record.version as string,
    release_url: record.release_url as string,
    download_url: record.download_url as string,
    published_at: record.published_at as string,
  };
}

function safeCached(value: unknown): CachedResult | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const record = value as Record<string, unknown>;
  if (!Number.isSafeInteger(record.checkedAt) || (record.status !== "up-to-date" && record.status !== "update-available" && record.status !== "retryable") || typeof record.currentVersion !== "string") return undefined;
  const parsed = parseVersion(record.currentVersion);
  if (!parsed) return undefined;
  let metadata: UpdateMetadata | undefined;
  if (record.metadata !== undefined) {
    try { metadata = parseUpdateMetadata(record.metadata); }
    catch { return undefined; }
  }
  if (record.status === "update-available" && !metadata) return undefined;
  return { checkedAt: record.checkedAt as number, status: record.status, currentVersion: record.currentVersion, ...(metadata ? { metadata } : {}), ...(typeof record.message === "string" ? { message: record.message.slice(0, 300) } : {}) };
}

function publicResult(cache: CachedResult): UpdateCheckResult {
  return { status: cache.status, current_version: cache.currentVersion, checked_at: cache.checkedAt, ...(cache.metadata ? { metadata: cache.metadata } : {}), ...(cache.message ? { message: cache.message } : {}) };
}

export class UpdateChecker {
  private inFlight: Promise<UpdateCheckResult> | undefined;
  private readonly storage: UpdateStorage;
  private readonly currentVersion: string;
  private readonly fetcher: UpdateFetcher;
  private readonly now: () => number;

  constructor(
    storage: UpdateStorage,
    currentVersion: string,
    fetcher: UpdateFetcher = (input, init) => fetch(input, init),
    now: () => number = () => Date.now(),
  ) {
    this.storage = storage;
    this.currentVersion = currentVersion;
    this.fetcher = fetcher;
    this.now = now;
    if (!parseVersion(currentVersion)) throw new Error("Invalid current extension version");
  }

  async check(options: { force?: boolean } = {}): Promise<UpdateCheckResult> {
    if (this.inFlight) return this.inFlight;
    this.inFlight = this.run(options.force === true).finally(() => { this.inFlight = undefined; });
    return this.inFlight;
  }

  private async run(force: boolean): Promise<UpdateCheckResult> {
    const now = this.now();
    const stored: Record<string, unknown> = await this.storage.get(UPDATE_CACHE_KEY).catch(() => ({} as Record<string, unknown>));
    const cached = safeCached(stored[UPDATE_CACHE_KEY]);
    if (cached && now >= cached.checkedAt && now - cached.checkedAt < UPDATE_CHECK_INTERVAL_MS && (cached.status !== "retryable" || !force)) return publicResult(cached);

    const checkedAt = now;
    try {
      const response = await this.fetcher(UPDATE_METADATA_URL, { method: "GET", cache: "no-store", credentials: "omit", redirect: "error" });
      if (!response.ok) throw new Error(`Update metadata request failed (${response.status})`);
      const metadata = parseUpdateMetadata(await response.json());
      const comparison = compareSemVer(metadata.version, this.currentVersion);
      if (comparison < 0) throw new Error("Update metadata is older than the installed extension");
      if (comparison === 0) {
        const result: CachedResult = { checkedAt, status: "up-to-date", currentVersion: this.currentVersion };
        await this.storage.set({ [UPDATE_CACHE_KEY]: result }).catch(() => undefined);
        return publicResult(result);
      }
      const result: CachedResult = { checkedAt, status: "update-available", currentVersion: this.currentVersion, metadata };
      await this.storage.set({ [UPDATE_CACHE_KEY]: result }).catch(() => undefined);
      return publicResult(result);
    } catch (error) {
      const result: CachedResult = { checkedAt, status: "retryable", currentVersion: this.currentVersion, message: error instanceof Error ? error.message : "Update check failed" };
      await this.storage.set({ [UPDATE_CACHE_KEY]: result }).catch(() => undefined);
      return publicResult(result);
    }
  }
}
