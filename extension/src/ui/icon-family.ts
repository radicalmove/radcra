export type ReviewIconName = "save" | "edit" | "delete" | "help";

/**
 * Inline Sphere identity mark for UI surfaces that cannot use packaged PNGs.
 * Keep this local and deliberately small: the blue geometric disk is the
 * sphere, while the white pill-and-tail is the restrained review cue shared
 * by the generated extension and Store artwork.
 */
export const sphereLogoMarkup = '<svg viewBox="0 0 128 128" aria-hidden="true" data-sphere-logo="true" role="img"><circle cx="64" cy="64" r="48" fill="#0C447C"></circle><circle cx="64" cy="64" r="44" fill="#185FA5"></circle><path d="M39 56a37 37 0 0 0 57 0" fill="none" stroke="#378ADD" stroke-width="3" stroke-linecap="round"></path><path d="M48 39a38 38 0 0 1 29 64" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"></path><rect x="43" y="56" width="42" height="14" rx="6" fill="#fff"></rect><path d="m51 68-4 10 14-9" fill="#fff"></path></svg>';

export function createSphereLogo(document: Document): SVGSVGElement {
  const container = document.createElement("div");
  container.innerHTML = sphereLogoMarkup;
  return container.firstElementChild as unknown as SVGSVGElement;
}

const iconContents: Record<ReviewIconName, string> = {
  save: '<path d="M5 3h11l3 3v15H5z"></path><path d="M8 3v6h8V3"></path><path d="M8 21v-7h8v7"></path>',
  edit: '<path d="M4 20l4.5-1 10-10a2.12 2.12 0 0 0-3-3l-10 10z"></path><path d="m14.5 7.5 3 3M5.5 16l3 3"></path>',
  delete: '<path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 11v6M14 11v6"></path>',
  help: '<circle cx="12" cy="12" r="9"></circle><path d="M9.75 9a2.4 2.4 0 1 1 3.38 2.2c-.75.36-1.13.9-1.13 1.8"></path><circle cx="12" cy="16.5" r="1" fill="currentColor" stroke="none"></circle>',
};

function setCommonAttributes(svg: SVGSVGElement, name: ReviewIconName): void {
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.dataset.reviewIcon = name;
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
}

export function reviewIconMarkup(name: ReviewIconName): string {
  return `<svg viewBox="0 0 24 24" aria-hidden="true" data-review-icon="${name}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${iconContents[name]}</svg>`;
}

export function createReviewIcon(document: Document, name: ReviewIconName): SVGSVGElement {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  setCommonAttributes(svg, name);
  svg.innerHTML = iconContents[name];
  return svg;
}
