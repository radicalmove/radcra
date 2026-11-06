const toggle = document.querySelector("#toggle");
const status = document.querySelector("#status");
let paused = false;
const render = () => {
  toggle.textContent = paused ? "Resume Sphere" : "Pause Sphere";
  status.textContent = paused ? "Sphere is paused in this Chrome profile." : "Sphere is on.";
  toggle.disabled = false;
};
chrome.storage.local.get("spherePaused").then((value) => {
  paused = value.spherePaused === true;
  render();
}).catch(() => { status.textContent = "Could not read Sphere’s settings."; });
toggle.onclick = async () => {
  toggle.disabled = true;
  try {
    await chrome.storage.local.set({ spherePaused: !paused });
    paused = !paused;
    render();
  } catch { status.textContent = "Could not change Sphere’s settings."; toggle.disabled = false; }
};
