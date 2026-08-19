/** Shared Sphere/CUBE-derived tokens for both Shadow DOM surfaces. */
declare const chrome: { runtime?: { getURL?: (value: string) => string } };

const fontUrl = (path: string): string => typeof chrome !== "undefined" && chrome.runtime?.getURL
  ? chrome.runtime.getURL(path)
  : path;

export const sphereFontFamily = "Poppins,system-ui,-apple-system,Segoe UI,Roboto,sans-serif";

export const sphereTokens = `@font-face{font-family:Poppins;font-style:normal;font-weight:400;font-display:swap;src:url("${fontUrl("fonts/Poppins-Regular.ttf")}") format("truetype")}@font-face{font-family:Poppins;font-style:normal;font-weight:500;font-display:swap;src:url("${fontUrl("fonts/Poppins-Medium.ttf")}") format("truetype")}@font-face{font-family:Poppins;font-style:normal;font-weight:600;font-display:swap;src:url("${fontUrl("fonts/Poppins-SemiBold.ttf")}") format("truetype")}@font-face{font-family:Poppins;font-style:normal;font-weight:700;font-display:swap;src:url("${fontUrl("fonts/Poppins-Bold.ttf")}") format("truetype")}:host{--sphere-ink:#0C447C;--sphere-primary:#185FA5;--sphere-action:#378ADD;--sphere-metadata:#4A78A8;--sphere-ground:#F4F9FF;--sphere-surface:#FFFFFF;--sphere-wash:#E6F1FB;--sphere-hover:#FAFCFF;--sphere-selected:#E6F1FB;--sphere-line:rgba(56,138,221,.2);--sphere-line-strong:rgba(56,138,221,.3);--sphere-success:#639922;--sphere-success-deep:#3B6D11;--sphere-success-wash:#E4F1EE;--sphere-warning:#E8A400;--sphere-warning-deep:#B07E00;--sphere-warning-wash:#FBEFCB;--sphere-danger:#D73B3D;--sphere-danger-hover:#B52D30;--sphere-danger-deep:#8E2A22;--sphere-danger-wash:#FCEBE8;--sphere-info:#378ADD;--sphere-focus:#378ADD;--sphere-action-wash:rgba(55,138,221,.2);--sphere-space-1:4px;--sphere-space-15:6px;--sphere-space-2:8px;--sphere-space-3:12px;--sphere-space-4:16px;--sphere-radius-control:6px;--sphere-radius-container:8px;--sphere-radius-small:4px;--sphere-font-family:${sphereFontFamily};--sphere-font-size:13px;--sphere-line-height:1.55;all:initial;box-sizing:border-box;font-family:var(--sphere-font-family);font-size:var(--sphere-font-size);line-height:var(--sphere-line-height);color:var(--sphere-ink)}`;

export const sphereTokenStyles = sphereTokens;
