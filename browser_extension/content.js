/**
 * SecureVault content script
 *
 * Save/Update fix
 * ───────────────
 * Previous approach used chrome.storage.session (async) — write never completed
 * before the page navigated away.
 *
 * Now uses sessionStorage (browser-native, synchronous, same-tab, cross-page):
 *   login.php  → beforeunload fires → sessionStorage.setItem() (sync, instant)
 *   dashboard.php loads → sessionStorage.getItem() → CHECK_CREDENTIAL → banner
 */

(function () {
  "use strict";
  if (window.__sv_injected) return;
  window.__sv_injected = true;

  const DOMAIN      = location.hostname.replace(/^www\./, "");
  const SESSION_KEY = "sv_pending_cred";   // sessionStorage key

  // ── Synthetic input (React / Vue / Angular safe) ──────────────────────────
  function simulateInput(el, value) {
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype, "value"
    )?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input",  { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function fillForm(userField, pwField, username, password) {
    if (userField && username) { userField.focus(); simulateInput(userField, username); }
    if (pwField  && password) { pwField.focus();   simulateInput(pwField,   password); }
  }

  // ── Find login forms ──────────────────────────────────────────────────────
  function findLoginForms() {
    return [...document.querySelectorAll("input[type='password']")].map(pw => {
      const root = pw.closest("form") || document.body;
      const candidates = [...root.querySelectorAll(
        "input[type='email'],input[type='text']," +
        "input[name*='user'],input[name*='login'],input[name*='email']," +
        "input[autocomplete*='username'],input[autocomplete*='email']"
      )];
      const user = candidates.reverse().find(
        el => el.compareDocumentPosition(pw) & Node.DOCUMENT_POSITION_FOLLOWING
      ) || candidates[0] || null;
      return { userField: user, pwField: pw };
    });
  }

  // ── Styles ────────────────────────────────────────────────────────────────
  function injectStyle() {
    if (document.getElementById("sv-style")) return;
    const s = document.createElement("style");
    s.id = "sv-style";
    s.textContent = `
      #sv-btn {
        position:fixed;bottom:22px;right:22px;z-index:2147483640;
        background:#89b4fa;color:#1e1e2e;border:none;border-radius:8px;
        padding:9px 16px;font:700 13px 'Segoe UI',sans-serif;
        cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.35);
      }
      #sv-btn:hover { background:#b4befe }
      #sv-picker {
        position:fixed;bottom:68px;right:22px;z-index:2147483641;
        background:#313244;border:1px solid #45475a;border-radius:10px;
        padding:12px;min-width:230px;box-shadow:0 8px 28px rgba(0,0,0,.55);
        font:13px 'Segoe UI',sans-serif;color:#cdd6f4;
      }
      .sv-head { font:700 11px 'Segoe UI',sans-serif;color:#89b4fa;
        text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px }
      .sv-item { display:block;width:100%;text-align:left;background:#45475a;
        border:none;border-radius:6px;padding:8px 12px;margin-bottom:6px;
        color:#cdd6f4;cursor:pointer;font-size:13px }
      .sv-item:hover { background:#585b70 }
      .sv-item strong { display:block }
      .sv-item small  { color:#a6adc8;font-size:11px }
      .sv-close { display:block;width:100%;background:transparent;
        border:1px solid #45475a;border-radius:6px;padding:5px;
        color:#a6adc8;cursor:pointer;font-size:12px }
      #sv-banner {
        position:fixed;top:0;left:0;right:0;z-index:2147483647;
        background:#1e1e2e;color:#cdd6f4;padding:12px 18px;
        display:flex;align-items:center;gap:10px;
        font:13px 'Segoe UI',sans-serif;
        box-shadow:0 3px 12px rgba(0,0,0,.5);
        border-bottom:2px solid #89b4fa;
      }
      #sv-banner .sv-text { flex:1;font-weight:700;color:#89b4fa }
      #sv-banner .sv-sub  { color:#a6adc8;font-size:11px;font-weight:400 }
      #sv-banner button   { border:none;border-radius:6px;padding:6px 14px;
        font:700 12px 'Segoe UI',sans-serif;cursor:pointer }
      #sv-banner .sv-yes  { background:#89b4fa;color:#1e1e2e }
      #sv-banner .sv-yes:hover { background:#b4befe }
      #sv-banner .sv-no   { background:#313244;color:#cdd6f4;margin-left:4px }
      #sv-banner .sv-x    { background:transparent;color:#585b70;
        font-size:18px;padding:2px 8px;margin-left:4px }
      #sv-toast {
        position:fixed;bottom:70px;right:22px;z-index:2147483641;
        background:#a6e3a1;color:#1e1e2e;padding:10px 16px;
        border-radius:8px;font:700 13px 'Segoe UI',sans-serif;
        box-shadow:0 4px 14px rgba(0,0,0,.3);
      }
      #sv-toast.err { background:#f38ba8 }
    `;
    document.head.appendChild(s);
  }

  function esc(s) {
    return (s||"").replace(/[&<>"']/g,c=>
      ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])
    );
  }
  function removeEl(id) { document.getElementById(id)?.remove(); }

  function showToast(msg, isError = false) {
    removeEl("sv-toast");
    const t = document.createElement("div");
    t.id = "sv-toast";
    t.textContent = msg;
    if (isError) t.classList.add("err");
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }

  // ── Autofill button + picker ──────────────────────────────────────────────
  function injectButton(forms) {
    removeEl("sv-btn");
    const btn = document.createElement("button");
    btn.id = "sv-btn";
    btn.textContent = "🔐 SecureVault";
    btn.onclick = () => {
      btn.textContent = "⏳…"; btn.disabled = true;
      chrome.runtime.sendMessage({ type: "GET_CREDENTIALS", url: location.href }, resp => {
        btn.textContent = "🔐 SecureVault"; btn.disabled = false;
        if (!resp)          { showToast("SecureVault: app not running?", true); return; }
        if (resp.error)     { showToast(resp.error, true); return; }
        const creds = resp.credentials || [];
        if (!creds.length)  { showToast("No saved credentials for this site."); return; }
        if (creds.length === 1) {
          fillForm(forms[0].userField, forms[0].pwField, creds[0].username, creds[0].password);
          removeEl("sv-btn");
        } else {
          showPicker(creds, forms[0]);
        }
      });
    };
    document.body.appendChild(btn);
  }

  function showPicker(creds, { userField, pwField }) {
    removeEl("sv-picker");
    const box = document.createElement("div"); box.id = "sv-picker";
    box.innerHTML =
      `<div class="sv-head">Choose credential</div>` +
      creds.map(c =>
        `<button class="sv-item" data-u="${esc(c.username)}" data-p="${esc(c.password)}">
           <strong>${esc(c.title)}</strong><small>${esc(c.username)}</small>
         </button>`
      ).join("") +
      `<button class="sv-close">✕  Close</button>`;
    box.querySelectorAll(".sv-item").forEach(btn => {
      btn.onclick = () => {
        fillForm(userField, pwField, btn.dataset.u, btn.dataset.p);
        removeEl("sv-picker"); removeEl("sv-btn");
      };
    });
    box.querySelector(".sv-close").onclick = () => removeEl("sv-picker");
    document.body.appendChild(box);
  }

  // ── Save / Update banner ──────────────────────────────────────────────────
  function showBanner(mode, pending, entryId) {
    removeEl("sv-banner");
    const isSave  = mode === "save";
    const bar = document.createElement("div"); bar.id = "sv-banner";
    bar.innerHTML = `
      <span style="font-size:18px">🔐</span>
      <div style="flex:1">
        <div class="sv-text">
          ${isSave ? "Save password to SecureVault?" : "Update saved password?"}
        </div>
        <div class="sv-sub">
          ${esc(pending.username)} on ${esc(DOMAIN)}
        </div>
      </div>
      <button class="sv-yes">${isSave ? "Save" : "Update"}</button>
      <button class="sv-no">Not now</button>
      <button class="sv-x">✕</button>
    `;

    bar.querySelector(".sv-yes").onclick = () => {
      if (isSave) {
        chrome.runtime.sendMessage({
          type: "SAVE_CREDENTIAL",
          url: pending.url, username: pending.username, password: pending.password,
        });
      } else {
        chrome.runtime.sendMessage({
          type: "UPDATE_CREDENTIAL",
          entry_id: entryId, password: pending.password,
        });
      }
      sessionStorage.removeItem(SESSION_KEY);
      removeEl("sv-banner");
      showToast(isSave ? "✅  Saved to SecureVault" : "✅  Updated in SecureVault");
    };

    bar.querySelector(".sv-no").onclick = () => {
      sessionStorage.removeItem(SESSION_KEY);
      removeEl("sv-banner");
    };
    bar.querySelector(".sv-x").onclick = () => removeEl("sv-banner");

    document.body.prepend(bar);
    setTimeout(() => removeEl("sv-banner"), 25_000);
  }

  // ════════════════════════════════════════════════════════════════════════════
  // STEP 1 — Capture credentials on THIS page before it navigates away
  // Uses beforeunload (synchronous) so the write always completes
  // ════════════════════════════════════════════════════════════════════════════

  let _hasPasswordForm = false;

  function captureBeforeLeave() {
    const forms = findLoginForms();
    if (!forms.length) return;
    _hasPasswordForm = true;

    window.addEventListener("beforeunload", () => {
      // Runs synchronously — page cannot navigate until this returns
      for (const { userField, pwField } of forms) {
        const password = pwField.value;
        if (!password) continue;
        const username = userField?.value?.trim() || "";
        // sessionStorage.setItem is synchronous — always completes before unload
        try {
          sessionStorage.setItem(SESSION_KEY, JSON.stringify({
            username,
            password,
            url:       location.href,
            domain:    DOMAIN,
            ts:        Date.now(),
          }));
        } catch (_) {}
        break;   // only save the first password field found
      }
    }, { once: true });
  }

  // ════════════════════════════════════════════════════════════════════════════
  // STEP 2 — On NEXT page load, check for a pending credential
  // ════════════════════════════════════════════════════════════════════════════

  function checkPendingCredential() {
    let raw;
    try { raw = sessionStorage.getItem(SESSION_KEY); } catch (_) { return; }
    if (!raw) return;

    let pending;
    try { pending = JSON.parse(raw); } catch (_) {
      sessionStorage.removeItem(SESSION_KEY); return;
    }

    // Expire after 2 minutes
    if (!pending.password || Date.now() - pending.ts > 120_000) {
      sessionStorage.removeItem(SESSION_KEY); return;
    }

    // Only act if we're on the same domain (login.php → dashboard.php ✅)
    if (pending.domain !== DOMAIN) return;

    // Don't show banner on a page that itself has a login form
    // (means the login probably failed and we're back on the login page)
    const formsHere = findLoginForms();
    if (formsHere.length > 0) {
      // Login failed — clear and don't show banner
      sessionStorage.removeItem(SESSION_KEY);
      return;
    }

    // Ask background to check the vault
    chrome.runtime.sendMessage(
      {
        type:     "CHECK_CREDENTIAL",
        url:      pending.url,
        username: pending.username,
        password: pending.password,
      },
      (resp) => {
        if (chrome.runtime.lastError) {
          // Extension not connected — silent fail
          return;
        }
        if (!resp || resp.action === "none") {
          sessionStorage.removeItem(SESSION_KEY);
          return;
        }
        if (resp.action === "save") {
          showBanner("save", pending, null);
        } else if (resp.action === "update") {
          showBanner("update", pending, resp.entry_id);
        }
      }
    );
  }

  // ── Messages from background (autofill fill command) ──────────────────────
  chrome.runtime.onMessage.addListener(msg => {
    if (msg.type === "FILL_FORM") {
      const forms = findLoginForms();
      if (forms.length) fillForm(forms[0].userField, forms[0].pwField, msg.username, msg.password);
    }
  });

  // ── Main ──────────────────────────────────────────────────────────────────
  function scan() {
    injectStyle();
    const forms = findLoginForms();
    if (!forms.length) return;
    if (!document.getElementById("sv-btn")) injectButton(forms);
    if (!_hasPasswordForm) captureBeforeLeave();
  }

  // Check for credentials saved by the PREVIOUS page
  checkPendingCredential();

  // Scan for login forms on THIS page
  scan();
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });

})();
