const fragment = location.hash.slice(1);
history.replaceState(null, "", location.pathname + location.search);
const email = document.querySelector("#sphere-signin-email");
if (email) {
  email.value = (new URLSearchParams(fragment).get("email") || "").slice(0, 320);
} else if (/^[A-Za-z0-9_-]{32,128}$/.test(fragment)) {
  document.querySelector("#sphere-email-proof").value = fragment;
  document.querySelector("#sphere-confirm-email").disabled = false;
}
