import type { PageComment } from "../background-bridge.ts";
import { recoverTextAnchor } from "../anchors/recover.ts";
import { quizActivityLink } from "../course-context.ts";

export function openReviewWorkspace(shadow: ShadowRoot, page: string, comments: PageComment[], checked: Set<string>, jump: (comment: PageComment) => void) {
  const document = shadow.ownerDocument;
  const dialog = document.createElement("dialog");
  dialog.dataset.reviewWorkspace = "true";
  dialog.setAttribute("aria-label", "Course review");
  dialog.style.cssText = "box-sizing:border-box;width:100vw;height:100dvh;max-width:none;max-height:none;margin:0;padding:24px;border:0;background:#f4f9ff;color:#0c447c;overflow:auto;";
  const make = <K extends keyof HTMLElementTagNameMap>(tag: K, text: string, parent: HTMLElement = dialog) => {
    const element = document.createElement(tag); element.textContent = text; parent.append(element); return element;
  };
  const rows = comments.map((comment: PageComment & { created_at?: string }) => {
    const original = comment.selected_quote;
    const found = original && comment.page_url === page && !comment.embedded_locator
      ? recoverTextAnchor(document, { selected_quote: original, prefix: comment.prefix ?? "", suffix: comment.suffix ?? "" })
      : undefined;
    const quiz = comment.page_title.includes(" — Quiz preview")
      ? quizActivityLink(comment.page_url) ?? (/\/mod\/quiz\/view\.php\?id=\d+$/.test(comment.page_url) ? comment.page_url : undefined)
      : undefined;
    return { id: comment.id, page: comment.page_title, url: quiz ?? comment.parent_activity_url ?? comment.page_url, quiz, author: comment.author.display_name, created_at: comment.created_at ?? null, status: comment.status, comment: comment.body, original, current: found?.status === "resolved" && !found.approximate ? found.range.toString() : null, history: comment.status_history };
  });
  const header = make("header", ""); header.style.cssText = "position:sticky;top:0;background:#f4f9ff;padding:8px 0;border-bottom:1px solid #bacde0;z-index:1;";
  make("h2", "Course review", header).style.margin = "0 0 8px";
  const toolbar = make("div", "", header); toolbar.style.cssText = "display:flex;flex-wrap:wrap;gap:8px;";
  make("button", "Close", toolbar).onclick = () => dialog.close();
  for (const format of ["csv", "json"] as const) make("button", "Export " + format.toUpperCase(), toolbar).onclick = () => {
    const records = rows.map((row) => ({ ...row, checked: checked.has(row.id) }));
    const cell = (value: unknown) => {
      let text = value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
      if (/^[\s]*[=+@-]|^[\t\r\n]/.test(text)) text = "'" + text;
      return '"' + text.replaceAll('"', '""') + '"';
    };
    const fields = ["id","page","url","author","created_at","status","comment","original","current","history","checked"] as const;
    const output = format === "json" ? JSON.stringify(records, null, 2) : [fields.join(","), ...records.map((row) => fields.map((field) => cell(row[field])).join(","))].join("\r\n");
    const url = URL.createObjectURL(new Blob([output], { type: format === "json" ? "application/json" : "text/csv" }));
    const link = make("a", ""); link.href = url; link.download = "sphere-course-review." + format; link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  for (const [index, row] of rows.entries()) {
    const article = make("article", ""); article.style.cssText = "border-bottom:1px solid #bacde0;padding:12px 0;";
    make("h3", row.page, article);
    make("p", row.author + " · " + (row.created_at ? new Date(row.created_at).toLocaleString() : "Date unavailable") + " · " + row.status, article);
    make("p", row.comment, article);
    if (row.original) { make("p", "Originally highlighted: " + row.original, article); make("p", "Current text: " + (row.current ?? "Not verified on this page"), article); }
    for (const event of row.history) make("p", event.status + " · " + event.actor + " · " + new Date(event.created_at).toLocaleString(), article);
    const actions = make("div", "", article); actions.style.cssText = "display:flex;align-items:center;flex-wrap:wrap;gap:12px;";
    const label = make("label", "", actions); label.style.cssText = "display:inline-flex;align-items:center;gap:8px;min-height:38px;";
    const box = make("input", "", label); box.type = "checkbox"; box.style.cssText = "width:20px;height:20px;min-height:0;margin:0;"; box.checked = checked.has(row.id); label.append("Reviewed this session");
    box.onchange = () => { if (box.checked) checked.add(row.id); else checked.delete(row.id); };
    make("button", "Go to comment", actions).onclick = () => { dialog.close(); jump(comments[index]); };
    if (row.quiz) { const link = make("a", "Open quiz activity", actions); link.href = row.quiz; }
  }
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  shadow.append(dialog); dialog.showModal();
}
