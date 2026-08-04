import type { PageComment } from "./background-bridge.ts";

const CONNECTED_PACKAGE_HOSTNAME = "packages.articulateusercontent.com";
const FALLBACK_LABEL = "We couldn't load this course";
const EMBEDDED_TITLE_PREFIX = "Embedded activity · ";
const CANONICAL_FALLBACK_TITLE = `${EMBEDDED_TITLE_PREFIX}${FALLBACK_LABEL}`;
const SYNTHETIC_HASH_PREFIX = "#moodle-review-page=";

export type ConnectedPackageTitleAliases = Map<string, Map<string, string>>;

function correctedTitle(event: unknown, activeCourseId: string | undefined): { pageUrl: string; title: string } | undefined {
  if (!activeCourseId || !event || typeof event !== "object") return undefined;
  const record = event as Record<string, unknown>;
  if (record.course_id !== activeCourseId || typeof record.page_url !== "string") return undefined;

  let parsed: URL;
  try { parsed = new URL(record.page_url); }
  catch { return undefined; }
  if (parsed.protocol !== "https:" || parsed.hostname !== CONNECTED_PACKAGE_HOSTNAME || !parsed.hash.startsWith(SYNTHETIC_HASH_PREFIX)) return undefined;
  try {
    if (decodeURIComponent(parsed.hash.slice(SYNTHETIC_HASH_PREFIX.length)) !== FALLBACK_LABEL) return undefined;
  } catch { return undefined; }

  if (!record.payload || typeof record.payload !== "object") return undefined;
  const title = (record.payload as Record<string, unknown>).page_title;
  if (typeof title !== "string"
    || title !== title.trim()
    || !title.startsWith(EMBEDDED_TITLE_PREFIX)
    || !title.slice(EMBEDDED_TITLE_PREFIX.length).trim()
    || title === CANONICAL_FALLBACK_TITLE) return undefined;
  return { pageUrl: record.page_url, title };
}

export function recordConnectedPackageTitleAlias(
  aliases: ConnectedPackageTitleAliases,
  activeCourseId: string | undefined,
  event: unknown,
): boolean {
  const alias = correctedTitle(event, activeCourseId);
  if (!alias || !activeCourseId) return false;
  let courseAliases = aliases.get(activeCourseId);
  if (!courseAliases) {
    courseAliases = new Map();
    aliases.set(activeCourseId, courseAliases);
  }
  courseAliases.set(alias.pageUrl, alias.title);
  return true;
}

export function applyConnectedPackageTitleAliases(
  comments: PageComment[],
  courseId: string | undefined,
  aliases: ConnectedPackageTitleAliases,
): PageComment[] {
  if (!courseId) return comments;
  const courseAliases = aliases.get(courseId);
  if (!courseAliases) return comments;

  let projected: PageComment[] | undefined;
  comments.forEach((comment, index) => {
    const title = courseAliases.get(comment.page_url);
    if (!title || comment.page_title !== CANONICAL_FALLBACK_TITLE) return;
    projected ??= comments.slice();
    projected[index] = { ...comment, page_title: title };
  });
  return projected ?? comments;
}
