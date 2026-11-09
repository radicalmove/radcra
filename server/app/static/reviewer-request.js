const proof = location.hash.slice(1);
history.replaceState(null, "", location.pathname);
if (/^[A-Za-z0-9_-]{32,128}$/.test(proof)) {
  document.querySelector("#sphere-email-proof").value = proof;
  document.querySelector("#sphere-confirm-email").disabled = false;
}
