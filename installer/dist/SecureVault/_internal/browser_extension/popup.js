// SecureVault — Copyright (c) 2026 Hossain Abedy Supta
// https://chromewebstore.google.com/detail/securevault/iehpbeonbgfhciidfllbdfjiphooechbs
/**
 * SecureVault popup script.
 *
 * 1. Ping native host → show connection status.
 * 2. Get current tab URL → ask for matching credentials.
 * 3. Render credential list; "Fill" button sends FILL_CREDENTIALS to background.
 */

const statusEl  = document.getElementById("status");
const credList  = document.getElementById("cred-list");

function setStatus(msg, cls = "") {
  statusEl.textContent      = msg;
  statusEl.className        = "status " + cls;
}

function escHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

async function currentTabUrl() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
      resolve(tab?.url || "");
    });
  });
}

async function init() {
  // ── 1. Ping ───────────────────────────────────────────────────────────────
  const ping = await new Promise((res) =>
    chrome.runtime.sendMessage({ type: "PING" }, res)
  );

  if (!ping || ping.error) {
    setStatus(
      "⚠  SecureVault app not running.\nLaunch the app and try again.",
      "error"
    );
    return;
  }

  // ── 2. Get current URL ────────────────────────────────────────────────────
  const url = await currentTabUrl();
  if (!url || url.startsWith("chrome://") || url.startsWith("edge://")) {
    setStatus("No credentials for browser pages.", "");
    return;
  }

  let domain = "";
  try {
    domain = new URL(url).hostname.replace(/^www\./, "");
  } catch {
    setStatus("Cannot parse page URL.", "error");
    return;
  }

  setStatus(`🔍  Searching for: ${domain}`);

  // ── 3. Fetch matching credentials ─────────────────────────────────────────
  const resp = await new Promise((res) =>
    chrome.runtime.sendMessage({ type: "GET_CREDENTIALS", url }, res)
  );

  if (!resp || resp.error) {
    setStatus("⚠  " + (resp?.error || "No response from app."), "error");
    return;
  }

  const creds = resp.credentials || [];

  if (creds.length === 0) {
    setStatus(`No saved credentials for ${domain}.`, "");
    credList.innerHTML = `
      <div class="empty">
        Add credentials in the<br>SecureVault desktop app.
      </div>`;
    return;
  }

  setStatus(`✅  ${creds.length} credential(s) found`, "ok");

  // ── 4. Render list ────────────────────────────────────────────────────────
  credList.innerHTML = "";
  creds.forEach((c) => {
    const li = document.createElement("li");
    li.className = "cred-item";
    li.innerHTML = `
      <div class="cred-info">
        <div class="cred-title">${escHtml(c.title)}</div>
        <div class="cred-user">${escHtml(c.username)}</div>
      </div>
      <button class="fill-btn">Fill</button>
    `;
    li.querySelector(".fill-btn").addEventListener("click", () => {
      chrome.runtime.sendMessage({
        type:     "FILL_CREDENTIALS",
        username: c.username,
        password: c.password,
      });
      window.close();
    });
    credList.appendChild(li);
  });
}

init();
