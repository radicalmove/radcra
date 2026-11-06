import { textNodes, type TextAnchor } from "./text.ts";

export type TextRecovery = { status: "resolved"; range: Range; approximate?: true } | { status: "unresolved"; reason: "absent" | "ambiguous" };

function boundary(nodes: Text[], offset: number): [Text, number] | null {
  let cursor = 0;
  for (const node of nodes) {
    if (offset <= cursor + node.length) return [node, offset - cursor];
    cursor += node.length;
  }
  return null;
}

export function recoverTextAnchor(document: Document, anchor: TextAnchor): TextRecovery {
  const nodes = textNodes(document); const all = nodes.map((node) => node.data).join("");
  const normalize = (value: string) => value.replace(/\s+/g, " ").trim();
  const normalizedQuote = normalize(anchor.selected_quote);
  if (!normalizedQuote) return { status: "unresolved", reason: "absent" };
  const chars: string[] = []; const offsets: number[] = []; let inWhitespace = false;
  for (let i = 0; i < all.length; i += 1) { const whitespace = /\s/.test(all[i]); if (whitespace) { if (!inWhitespace && chars.length) { chars.push(" "); offsets.push(i); } } else { chars.push(all[i]); offsets.push(i); } inWhitespace = whitespace; }
  const normalizedAll = chars.join("").trimEnd();
  const candidates: number[] = [];
  const prefix = normalize(anchor.prefix); const suffix = normalize(anchor.suffix);
  for (let index = normalizedAll.indexOf(normalizedQuote); index >= 0; index = normalizedAll.indexOf(normalizedQuote, index + 1)) {
    const prefixMatches = !prefix || normalize(normalizedAll.slice(Math.max(0, index - prefix.length - 2), index)).endsWith(prefix);
    const end = index + normalizedQuote.length;
    const suffixMatches = !suffix || normalize(normalizedAll.slice(end, end + suffix.length + 2)).startsWith(suffix);
    if (prefixMatches && suffixMatches) { candidates.push(index); if (candidates.length > 1) return { status: "unresolved", reason: "ambiguous" }; }
  }
  let from = candidates[0];
  let to = from + normalizedQuote.length;
  let approximate = false;
  const edited = candidates.length === 0;
  if (edited) {
    if (prefix.length < 12 || suffix.length < 12 || normalizedAll.includes(normalizedQuote)) return { status: "unresolved", reason: "absent" };
    const left = normalizedAll.indexOf(prefix);
    const right = normalizedAll.indexOf(suffix, left + prefix.length);
    if (left < 0 || right < 0 || normalizedAll.lastIndexOf(prefix) !== left || normalizedAll.lastIndexOf(suffix) !== right) return { status: "unresolved", reason: "absent" };
    from = left + prefix.length; to = right;
    while (from < to && normalizedAll[from] === " ") from++;
    while (from < to && normalizedAll[to - 1] === " ") to--;
    if (to - from > Math.max(160, normalizedQuote.length * 3)) return { status: "unresolved", reason: "absent" };
    if (to <= from) {
      const leftNode = boundary(nodes, offsets[left + prefix.length - 1])?.[0];
      const rightNode = boundary(nodes, offsets[right])?.[0];
      if (!leftNode || leftNode.parentElement !== rightNode?.parentElement) return { status: "unresolved", reason: "absent" };
      from = left + prefix.length - 1; to = from + 1; approximate = true;
    }
  }
  const rawStart = offsets[from]; const last = offsets[to - 1]; const rawEnd = last + 1;
  const start = boundary(nodes, rawStart); const end = boundary(nodes, rawEnd);
  if (!start || !end) return { status: "unresolved", reason: "absent" };
  if (edited && start[0].parentElement !== end[0].parentElement) return { status: "unresolved", reason: "absent" };
  const range = document.createRange(); range.setStart(...start); range.setEnd(...end);
  return approximate ? { status: "resolved", range, approximate: true } : { status: "resolved", range };
}

export function inaccessibleFrameFallback() {
  return { kind: "parent_pin" as const, label: "embedded content—frame access unavailable", prompt: "Place a pin on the embedded content instead" };
}

export function renderTextHighlight(document: Document, range: Range, onMount?: (highlight: HTMLElement) => void): () => void {
  const container = document.createElement("div"); container.setAttribute("data-moodle-review-highlight", "true");
  const place = () => { container.replaceChildren(); const rects = Array.from(range.getClientRects?.() ?? []); const boxes = rects.length ? rects : [range.getBoundingClientRect()]; const first = boxes[0]; container.style.cssText = `--sphere-action-wash:rgba(55,138,221,.2);position:fixed;pointer-events:none;z-index:899;background:var(--sphere-action-wash);border-radius:4px;left:${first.left}px;top:${first.top}px;width:${first.width}px;height:${first.height}px`; for (const rect of boxes.slice(1)) { const box = document.createElement("div"); box.style.cssText = `--sphere-action-wash:rgba(55,138,221,.2);position:fixed;pointer-events:none;z-index:899;background:var(--sphere-action-wash);border-radius:4px;left:${rect.left}px;top:${rect.top}px;width:${rect.width}px;height:${rect.height}px`; container.append(box); } };
  document.documentElement.append(container); place(); onMount?.(container);
  document.defaultView?.addEventListener("resize", place);
  document.defaultView?.addEventListener("scroll", place, true);
  return () => { document.defaultView?.removeEventListener("resize", place); document.defaultView?.removeEventListener("scroll", place, true); container.remove(); };
}
