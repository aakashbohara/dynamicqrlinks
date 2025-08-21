// ---------- API helpers ----------
const API = {
  login: () => "/login",
  create: () => "/create",
  links: () => "/links",
  update: (code) => `/update/${encodeURIComponent(code)}`,
  qr: (code) => `/qr/${encodeURIComponent(code)}`,
  short: (code) => `/${encodeURIComponent(code)}`, // pretty path
};

let PUBLIC_BASE = window.location.origin; // fallback if /config isn't provided
async function loadConfig() {
  try {
    const res = await fetch("/config", { credentials: "same-origin" });
    if (res.ok) {
      const cfg = await res.json();
      if (cfg && cfg.public_base_url) PUBLIC_BASE = cfg.public_base_url;
    }
  } catch {}
}

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

// ---------- Toasts ----------
const ensureToastWrap = () => {
  if (!$("#toast")) {
    const d = document.createElement("div");
    d.id = "toast";
    document.body.appendChild(d);
  }
};
const toast = (msg, type = "info") => {
  ensureToastWrap();
  const wrap = $("#toast");
  const el = document.createElement("div");
  el.className = `toast toast--${type}`;
  el.textContent = msg;
  wrap.appendChild(el);
  requestAnimationFrame(() => {
    el.classList.add("show");
    setTimeout(() => {
      el.classList.remove("show");
      setTimeout(() => el.remove(), 180);
    }, 2400);
  });
};

// ---------- Auth ----------
const tokenKey = "token";
const getToken = () => localStorage.getItem(tokenKey);
const setToken = (t) => localStorage.setItem(tokenKey, t);
const clearToken = () => localStorage.removeItem(tokenKey);

async function fetchJSON(url, opts = {}, { auth = false } = {}) {
  const headers = new Headers(opts.headers || {});
  if (
    !headers.has("Content-Type") &&
    opts.body &&
    !(opts.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }
  if (auth) {
    const t = getToken();
    if (!t) {
      window.location = "/";
      throw new Error("Unauthorized");
    }
    headers.set("Authorization", `Bearer ${t}`);
  }
  const res = await fetch(url, {
    ...opts,
    headers,
    credentials: "same-origin",
  });
  let data = null;
  try {
    data = await res.json();
  } catch {}
  if (!res.ok) {
    if (res.status === 401) {
      clearToken();
      toast("Session expired. Please sign in again.", "error");
      window.location = "/";
    }
    const msg =
      (data && (data.detail || data.message)) ||
      `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

// ---------- Login ----------
const loginForm = $("#loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(loginForm);
    try {
      const body = new URLSearchParams(fd);
      const data = await fetchJSON(API.login(), {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      setToken(data.access_token);
      toast("Signed in", "success");
      window.location = "/dashboard";
    } catch (err) {
      $("#msg") && ($("#msg").textContent = err.message);
      toast(err.message, "error");
    }
  });
}

// ---------- Dashboard ----------
const createForm = $("#createForm");
const linksWrap = $("#links");
const skeleton = $("#skeleton");
const emptyState = $("#emptyState");
const createMsg = $("#createMsg");
const logoutBtn = $("#logoutBtn");
const searchInput = $("#searchInput");

const ensureAuthed = () => {
  if (!getToken() && (createForm || linksWrap)) window.location = "/";
};

const qrCache = new Map(); // code -> base64

async function base64ToBlobUrl(b64) {
  const byteString = atob(b64);
  const bytes = new Uint8Array(byteString.length);
  for (let i = 0; i < byteString.length; i++)
    bytes[i] = byteString.charCodeAt(i);
  const blob = new Blob([bytes], { type: "image/png" });
  return URL.createObjectURL(blob);
}

async function loadLinks() {
  skeleton && (skeleton.style.display = "block");
  emptyState && (emptyState.style.display = "none");
  linksWrap && (linksWrap.innerHTML = "");
  try {
    const list = await fetchJSON(
      API.links(),
      { method: "GET" },
      { auth: true }
    );
    return Array.isArray(list) ? list : [];
  } catch (e) {
    toast(e.message, "error");
    return [];
  } finally {
    skeleton && (skeleton.style.display = "none");
  }
}

function renderOneLink(item) {
  const code = item.code;
  const absShort = `${PUBLIC_BASE}/${code}`;
  const shortHref = API.short(code);

  const card = document.createElement("div");
  card.className = "linkcard";
  const left = document.createElement("div");
  left.className = "linkcard__main";
  left.innerHTML = `
    <div class="linkcard__head">
      <div class="chip">${code}</div>
      <div class="stats">${item.click_count ?? 0} clicks</div>
    </div>

    <div class="row">
      <div class="tiny muted">Short URL</div>
      <div class="row-actions">
        <a class="mono" href="${shortHref}" target="_blank" rel="noopener">${absShort}</a>
        <button class="btn btn--sm btn--ghost copy-btn" title="Copy" data-copy="${absShort}">Copy</button>
        <button class="btn btn--sm btn--ghost open-btn" title="Open" data-href="${shortHref}">Open</button>
      </div>
    </div>

    <div class="row view-target">
      <div class="tiny muted">Target</div>
      <div class="row-actions">
        <a class="mono clamp" href="${
          item.target_url
        }" target="_blank" rel="noopener">${item.target_url}</a>
        <button class="btn btn--sm btn--ghost edit-btn">Edit</button>
      </div>
    </div>

    <div class="row edit-target" style="display:none;">
      <div class="tiny muted">Edit target</div>
      <div class="edit-inline">
        <input class="edit-input" type="url" value="${
          item.target_url
        }" placeholder="https://example.com" />
        <button class="btn btn--sm btn--primary save-btn">Save</button>
        <button class="btn btn--sm btn--ghost cancel-btn">Cancel</button>
      </div>
      <div class="tiny muted" style="margin-top:6px;">Code stays <strong>${code}</strong>, only the destination changes.</div>
    </div>
  `;
  const right = document.createElement("div");
  right.className = "qr";
  right.innerHTML = `
    <img id="qr-${code}" alt="QR for ${code}" />
    <button class="btn btn--secondary btn--sm dl-btn">Download PNG</button>
  `;

  card.appendChild(left);
  card.appendChild(right);
  linksWrap.appendChild(card);

  $(".copy-btn", card)?.addEventListener("click", async (e) => {
    try {
      await navigator.clipboard.writeText(e.currentTarget.dataset.copy);
      toast("Copied to clipboard", "success");
    } catch {
      toast("Copy failed", "error");
    }
  });
  $(".open-btn", card)?.addEventListener("click", (e) => {
    const href = e.currentTarget.dataset.href;
    if (href) window.open(href, "_blank", "noopener");
  });
  $(".edit-btn", card)?.addEventListener("click", () => {
    $(".view-target", card).style.display = "none";
    $(".edit-target", card).style.display = "block";
  });
  $(".cancel-btn", card)?.addEventListener("click", () => {
    $(".edit-target", card).style.display = "none";
    $(".view-target", card).style.display = "block";
  });
  $(".save-btn", card)?.addEventListener("click", async () => {
    const value = $(".edit-input", card).value.trim();
    if (!value) return toast("Enter a valid URL", "error");
    try {
      await fetchJSON(
        API.update(code),
        { method: "PATCH", body: JSON.stringify({ target_url: value }) },
        { auth: true }
      );
      toast("Updated", "success");
      $(".view-target a", card).textContent = value;
      $(".view-target a", card).href = value;
      $(".edit-target", card).style.display = "none";
      $(".view-target", card).style.display = "block";
    } catch (e) {
      toast(e.message, "error");
    }
  });

  (async () => {
    try {
      let b64 = qrCache.get(code);
      if (!b64) {
        const data = await fetchJSON(API.qr(code), { method: "GET" });
        b64 = data.qr_base64;
        qrCache.set(code, b64);
      }
      const img = $(`#qr-${code}`, card);
      img.src = `data:image/png;base64,${b64}`;
      $(".dl-btn", card)?.addEventListener("click", async () => {
        const url = await base64ToBlobUrl(b64);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${code}.png`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      });
    } catch {
      toast("Failed to load QR", "error");
    }
  })();
}

function renderLinks(list) {
  linksWrap.innerHTML = "";
  if (!list.length) {
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";
  list.forEach(renderOneLink);
}

// Create
if (createForm) {
  createForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    createMsg && (createMsg.textContent = "");
    const payload = {
      target_url: createForm.target_url.value.trim(),
      code: (createForm.code.value || "").trim() || null,
    };
    if (!payload.target_url) return toast("Target URL is required", "error");
    try {
      await fetchJSON(
        API.create(),
        { method: "POST", body: JSON.stringify(payload) },
        { auth: true }
      );
      toast("Created", "success");
      createForm.reset();
      await initDashboard();
    } catch (e) {
      createMsg && (createMsg.textContent = e.message);
      toast(e.message, "error");
    }
  });
}

// Search
if (searchInput && linksWrap) {
  searchInput.addEventListener("input", () => {
    const q = searchInput.value.toLowerCase();
    $$(".linkcard", linksWrap).forEach((card) => {
      const text = card.textContent.toLowerCase();
      card.style.display = text.includes(q) ? "" : "none";
    });
  });
}

// Logout (single declaration)
if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try {
      await fetch("/logout", { method: "POST", credentials: "same-origin" });
    } catch {}
    localStorage.removeItem("token");
    window.location = "/";
  });
}

// Init
async function initDashboard() {
  if (!getToken() && (createForm || linksWrap)) {
    window.location = "/";
    return;
  }
  await loadConfig();
  const list = await loadLinks();
  renderLinks(list);
}
if (linksWrap || createForm) initDashboard();
