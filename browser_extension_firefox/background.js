/**
 * SecureVault — background service worker  (enhanced)
 *
 * Routes all messages between content scripts / popup and the native host.
 *
 * Message types from content / popup → background
 * ─────────────────────────────────────────────────
 *   PING                                      → forward to native host
 *   GET_CREDENTIALS    { url }                → forward to native host
 *   CHECK_CREDENTIAL   { url, username, password } → check then reply SHOW_*_PROMPT
 *   SAVE_CREDENTIAL    { url, username, password } → forward to native host
 *   UPDATE_CREDENTIAL  { entry_id, password }      → forward to native host
 *   FILL_CREDENTIALS   { username, password }  → forward to active tab content script
 */

const HOST = "com.securevault.nativehost";

// ── Helper: call native host and get response ─────────────────────────────────
function callHost(msg) {
  return new Promise((resolve) => {
    chrome.runtime.sendNativeMessage(HOST, msg, (resp) => {
      if (chrome.runtime.lastError) {
        resolve({ error: chrome.runtime.lastError.message });
      } else {
        resolve(resp || { error: "Empty response from host." });
      }
    });
  });
}

// ── Helper: send message to the active tab's content script ──────────────────
async function sendToActiveTab(msg) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab) chrome.tabs.sendMessage(tab.id, msg).catch(() => {});
}

// ── Helper: send message to a specific tab ────────────────────────────────────
function sendToTab(tabId, msg) {
  chrome.tabs.sendMessage(tabId, msg).catch(() => {});
}

// ── Main message listener ─────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // PING — check native host is alive
  if (msg.type === "PING") {
    callHost({ action: "ping" }).then(sendResponse);
    return true;
  }

  // GET_CREDENTIALS — fetch matching entries for a URL (popup + content button)
  if (msg.type === "GET_CREDENTIALS") {
    let domain = "";
    try { domain = new URL(msg.url).hostname.replace(/^www\./, ""); } catch { }
    callHost({ action: "get_credentials", domain }).then(sendResponse);
    return true;
  }

  // CHECK_CREDENTIAL — content script asks whether to show save/update banner.
  // Must return true to keep the message channel open for the async response.
  if (msg.type === "CHECK_CREDENTIAL") {
    let domain = "";
    try { domain = new URL(msg.url).hostname.replace(/^www\./, ""); } catch { }

    callHost({
      action:   "check_credential",
      domain,
      username: msg.username,
      password: msg.password,
    }).then((resp) => {
      if (!resp || resp.error) {
        sendResponse({ action: "none" });
        return;
      }
      if (!resp.exists) {
        sendResponse({ action: "save" });
      } else if (resp.password_changed) {
        sendResponse({ action: "update", entry_id: resp.entry_id });
      } else {
        sendResponse({ action: "none" });
      }
    });
    return true;  // ← keeps channel open until sendResponse fires
  }

  // SAVE_CREDENTIAL — user clicked Save in the banner
  if (msg.type === "SAVE_CREDENTIAL") {
    let domain = "";
    try { domain = new URL(msg.url).hostname.replace(/^www\./, ""); } catch { }
    callHost({
      action:   "save_credential",
      url:      msg.url,
      username: msg.username,
      password: msg.password,
      title:    domain,
    }).then((resp) => {
      if (resp?.success && sender.tab?.id) {
        sendToTab(sender.tab.id, { type: "CREDENTIAL_SAVED" });
      }
    });
    return false;
  }

  // UPDATE_CREDENTIAL — user clicked Update in the banner
  if (msg.type === "UPDATE_CREDENTIAL") {
    callHost({
      action:   "update_credential",
      entry_id: msg.entry_id,
      password: msg.password,
    }).then((resp) => {
      if (resp?.success && sender.tab?.id) {
        sendToTab(sender.tab.id, { type: "CREDENTIAL_UPDATED" });
      }
    });
    return false;
  }

  // FILL_CREDENTIALS — popup chose a credential → inject into active tab
  if (msg.type === "FILL_CREDENTIALS") {
    sendToActiveTab({
      type:     "FILL_FORM",
      username: msg.username,
      password: msg.password,
    });
    return false;
  }

  return false;
});
