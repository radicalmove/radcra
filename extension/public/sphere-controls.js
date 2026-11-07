const toggle = document.querySelector("#toggle");
const status = document.querySelector("#status");
const updated = document.querySelector("#updated");
const dismissUpdate = document.querySelector("#dismiss-update");
let paused = false;
const render = () => {
  toggle.textContent = paused ? "Resume Sphere" : "Pause Sphere";
  status.textContent = paused ? "Sphere is paused in this Chrome profile." : "Sphere is on.";
  toggle.disabled = false;
};
chrome.storage.local.get(["spherePaused", "sphereUpdatedVersion"]).then((value) => {
  paused = value.spherePaused === true;
  if (value.sphereUpdatedVersion === chrome.runtime.getManifest().version) {
    updated.textContent = `Sphere updated to v${value.sphereUpdatedVersion}.`;
    updated.hidden = dismissUpdate.hidden = false;
  }
  render();
}).catch(() => { status.textContent = "Could not read Sphere’s settings."; });
dismissUpdate.onclick = async () => {
  try {
    await chrome.action.setBadgeText({ text: "" });
    await chrome.storage.local.remove("sphereUpdatedVersion");
    updated.hidden = dismissUpdate.hidden = true;
  } catch { updated.textContent = "Could not dismiss the update notice. Try again."; }
};
toggle.onclick = async () => {
  toggle.disabled = true;
  try {
    await chrome.storage.local.set({ spherePaused: !paused });
    paused = !paused;
    render();
  } catch { status.textContent = "Could not change Sphere’s settings."; toggle.disabled = false; }
};
