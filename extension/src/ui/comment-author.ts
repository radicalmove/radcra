/** Return the deterministic, display-only first token of a comment author's name. */
export function getCommentAuthorFirstName(author: unknown): string | undefined {
  if (!author || typeof author !== "object") return undefined;
  const displayName = (author as { display_name?: unknown }).display_name;
  if (typeof displayName !== "string") return undefined;
  const firstToken = displayName.trim().split(/\s+/)[0];
  return firstToken || undefined;
}

