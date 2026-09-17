/**
 * app.js - Logika Frontend Gemini Pro Ultra-Cepat
 * Menangani Streaming SSE, Rendering Markdown, Admin Storage Manager, & Voice Input.
 */

// ==========================================
// STATE & AUTH GLOBALS
// ==========================================
let currentUser = null;
try {
  currentUser = JSON.parse(localStorage.getItem("cipuy_auth_user") || "null");
} catch (e) {
  currentUser = null;
}

let isAdmin = currentUser ? currentUser.role === "admin" : false;
let adminSecretKey = localStorage.getItem("gemini_admin_key") || "";
let currentSessionId = localStorage.getItem("gemini_current_session") || null;
let isGenerating = false;

// ==========================================
// DOM ELEMENT REFERENCES
// ==========================================
let sidebar, toggleSidebarBtn, mobileMenuBtn, sidebarBackdrop, newChatBtn;
let sessionsList, heroGreeting, messagesList, chatScrollArea, promptInput, sendBtn, micBtn;
let roleBadgeBtn, roleBadgeText, userProfilePill, userProfileName, openAdminBtn;
let adminModal, closeAdminBtn, adminSearchInput, adminLogsTableBody, btnCleanOld, btnWipeAll;

function initDomReferences() {
  sidebar = document.getElementById("sidebar");
  toggleSidebarBtn = document.getElementById("toggleSidebarBtn");
  mobileMenuBtn = document.getElementById("mobileMenuBtn");
  sidebarBackdrop = document.getElementById("sidebarBackdrop");
  newChatBtn = document.getElementById("newChatBtn");
  sessionsList = document.getElementById("sessionsList");
  heroGreeting = document.getElementById("heroGreeting");
  messagesList = document.getElementById("messagesList");
  chatScrollArea = document.getElementById("chatScrollArea");
  promptInput = document.getElementById("promptInput");
  sendBtn = document.getElementById("sendBtn");
  micBtn = document.getElementById("micBtn");
  roleBadgeBtn = document.getElementById("roleBadgeBtn");
  roleBadgeText = document.getElementById("roleBadgeText");
  userProfilePill = document.getElementById("userProfilePill");
  userProfileName = document.getElementById("userProfileName");
  openAdminBtn = document.getElementById("openAdminBtn");
  adminModal = document.getElementById("adminModal");
  closeAdminBtn = document.getElementById("closeAdminBtn");
  adminSearchInput = document.getElementById("adminSearchInput");
  adminLogsTableBody = document.getElementById("adminLogsTableBody");
  btnCleanOld = document.getElementById("btnCleanOld");
  btnWipeAll = document.getElementById("btnWipeAll");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDomReferences);
} else {
  initDomReferences();
}

// ==========================================
// SIDEBAR & DRAWER NAVIGATION (HP & LAPTOP)
// ==========================================
function openMobileSidebar() {
  initDomReferences();
  if (sidebar) sidebar.classList.add("mobile-open");
  if (sidebarBackdrop) sidebarBackdrop.classList.add("active");
}
window.openMobileSidebar = openMobileSidebar;

function closeMobileSidebar() {
  initDomReferences();
  if (sidebar) sidebar.classList.remove("mobile-open");
  if (sidebarBackdrop) sidebarBackdrop.classList.remove("active");
}
window.closeMobileSidebar = closeMobileSidebar;

function toggleSidebar() {
  initDomReferences();
  if (sidebar) sidebar.classList.toggle("collapsed");
}
window.toggleSidebar = toggleSidebar;

function handleNewChat() {
  closeMobileSidebar();
  startNewChat();
}
window.handleNewChat = handleNewChat;

// Helper sesi milik user saat ini
function getMySessionIds() {
  try {
    const userPrefix = currentUser ? currentUser.username + "_" : "";
    return JSON.parse(localStorage.getItem("cipuy_sessions_" + userPrefix) || "[]");
  } catch (e) {
    return [];
  }
}

function addMySessionId(id) {
  const list = getMySessionIds();
  if (!list.includes(id)) {
    list.push(id);
    const userPrefix = currentUser ? currentUser.username + "_" : "";
    localStorage.setItem("cipuy_sessions_" + userPrefix, JSON.stringify(list));
  }
}

// Atur Intensitas Background Maskot
window.setMascotBg = function(level, btn) {
  const layer = document.getElementById("mascotBgLayer");
  if (!layer) return;
  document.querySelectorAll('.bg-mode-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  layer.className = 'mascot-hero-background-layer ' + level;
  try {
    localStorage.setItem("cipuy_mascot_bg_level", level);
  } catch(e) {}
};

// ==========================================
// UPFRONT AUTHENTICATION & LOGIN GATE
// ==========================================

function checkAuthGate() {
  const gate = document.getElementById("loginOverlayGate");
  const gateError = document.getElementById("gateLoginError");

  if (!currentUser || !currentUser.username) {
    if (gate) {
      gate.classList.remove("hidden");
      gate.style.display = "flex";
    }
    updateRoleUI();
    return false;
  }

  // Pengguna sudah login
  if (gate) {
    gate.classList.add("hidden");
    gate.style.display = "none";
  }
  if (gateError) gateError.style.display = "none";
  updateRoleUI();
  return true;
}

async function handleGateLoginSubmit(event) {
  if (event) event.preventDefault();
  const usernameInput = document.getElementById("gateUsernameInput");
  const passwordInput = document.getElementById("gatePasswordInput");
  const errorBanner = document.getElementById("gateLoginError");
  const loginBtn = document.getElementById("gateLoginBtn");

  const username = usernameInput ? usernameInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value.trim() : "";

  if (!username || !password) {
    if (errorBanner) {
      errorBanner.innerText = "Harap masukkan username dan password.";
      errorBanner.style.display = "flex";
    }
    return;
  }

  if (loginBtn) {
    loginBtn.disabled = true;
    loginBtn.innerHTML = `<span>Memverifikasi...</span>`;
  }
  if (errorBanner) errorBanner.style.display = "none";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "Login gagal. Periksa username dan password Anda.");
    }

    // Login Berhasil!
    currentUser = data.user;
    isAdmin = currentUser.role === "admin";
    adminSecretKey = data.secret_key || "";

    localStorage.setItem("cipuy_auth_user", JSON.stringify(currentUser));
    localStorage.setItem("cipuy_is_admin", isAdmin ? "true" : "false");
    if (adminSecretKey) {
      localStorage.setItem("gemini_admin_key", adminSecretKey);
    } else {
      localStorage.removeItem("gemini_admin_key");
    }

    // Sembunyikan Gerbang Login
    const gate = document.getElementById("loginOverlayGate");
    if (gate) {
      gate.classList.add("hidden");
      gate.style.display = "none";
    }

    if (passwordInput) passwordInput.value = "";

    updateRoleUI();
    loadSessions();
    if (!currentSessionId) {
      showHero();
    } else {
      loadSessionMessages(currentSessionId);
    }

  } catch (err) {
    if (errorBanner) {
      errorBanner.innerText = err.message || "Gagal menghubungi server.";
      errorBanner.style.display = "flex";
    }
  } finally {
    if (loginBtn) {
      loginBtn.disabled = false;
      loginBtn.innerHTML = `<span>Masuk</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>`;
    }
  }
}
window.handleGateLoginSubmit = handleGateLoginSubmit;

function handleLogout() {
  if (!confirm("Apakah Anda yakin ingin keluar dari akun?")) return;

  currentUser = null;
  isAdmin = false;
  adminSecretKey = "";
  currentSessionId = null;

  localStorage.removeItem("cipuy_auth_user");
  localStorage.removeItem("cipuy_is_admin");
  localStorage.removeItem("gemini_admin_key");
  localStorage.removeItem("gemini_current_session");

  closeAdminModal();
  closeMobileSidebar();

  // Reset pesan obrolan
  if (messagesList) messagesList.innerHTML = "";
  showHero();

  // Tampilkan kembali login gate
  const gate = document.getElementById("loginOverlayGate");
  const gateError = document.getElementById("gateLoginError");
  const uInput = document.getElementById("gateUsernameInput");
  const pInput = document.getElementById("gatePasswordInput");
  if (gate) {
    gate.classList.remove("hidden");
    gate.style.display = "flex";
  }
  if (gateError) gateError.style.display = "none";
  if (pInput) pInput.value = "";
  if (uInput) {
    uInput.value = "";
    uInput.focus();
  }

  updateRoleUI();
}
window.handleLogout = handleLogout;

function updateRoleUI() {
  initDomReferences();
  const profileName = document.getElementById("userProfileName");
  const openAdminBtn = document.getElementById("openAdminBtn");

  if (currentUser) {
    if (profileName) profileName.innerText = currentUser.username;
    if (isAdmin) {
      if (roleBadgeBtn) {
        roleBadgeBtn.className = "role-badge-pill admin-mode";
        roleBadgeBtn.title = "Mode Pemilik/Admin Aktif (Klik untuk Buka Panel)";
      }
      if (roleBadgeText) roleBadgeText.innerText = "👑 Admin (" + currentUser.username + ")";
      if (openAdminBtn) openAdminBtn.style.display = "flex";
    } else {
      if (roleBadgeBtn) {
        roleBadgeBtn.className = "role-badge-pill user-mode";
        roleBadgeBtn.title = "Pengguna Aktif: " + currentUser.username;
      }
      if (roleBadgeText) roleBadgeText.innerText = "User (" + currentUser.username + ")";
      if (openAdminBtn) openAdminBtn.style.display = "none";
    }
  } else {
    if (profileName) profileName.innerText = "Tamu";
    if (roleBadgeText) roleBadgeText.innerText = "Login";
    if (openAdminBtn) openAdminBtn.style.display = "none";
  }
}

// Konfigurasi marked.js untuk rendering markdown
if (window.marked) {
  marked.setOptions({
    breaks: true,
    gfm: true,
    highlight: function(code, lang) {
      if (window.hljs) {
        const validLang = hljs.getLanguage(lang) ? lang : "plaintext";
        return hljs.highlight(code, { language: validLang }).value;
      }
      return code;
    }
  });
}

// Inisialisasi saat halaman dimuat
document.addEventListener("DOMContentLoaded", () => {
  const isAuth = checkAuthGate();
  if (isAuth) {
    loadSessions();
    if (currentSessionId) {
      loadSessionMessages(currentSessionId);
    } else {
      showHero();
    }
  }

  setupEventListeners();
  setupTextareaAutoResize();

  // Kembalikan preferensi intensitas background maskot jika ada
  try {
    const savedBg = localStorage.getItem("cipuy_mascot_bg_level");
    if (savedBg) {
      const btn = Array.from(document.querySelectorAll('.bg-mode-btn')).find(b => b.innerText.toLowerCase().includes(savedBg) || (savedBg === 'medium' && b.innerText.includes('30%')));
      window.setMascotBg(savedBg, btn);
    }
  } catch(e) {}
});

function setupEventListeners() {
  initDomReferences();

  // Toggle Sidebar Desktop
  if (toggleSidebarBtn) {
    toggleSidebarBtn.addEventListener("click", toggleSidebar);
  }

  // Mobile Hamburger Menu
  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener("click", openMobileSidebar);
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", closeMobileSidebar);
  }

  // Tombol New Chat
  if (newChatBtn) {
    newChatBtn.addEventListener("click", handleNewChat);
  }

  // Role Badge Pill (Klik untuk Buka Admin bila Admin)
  if (roleBadgeBtn) {
    roleBadgeBtn.addEventListener("click", handleRoleBadgeClick);
  }

  // Tombol Database & Storage (Admin) di Sidebar
  if (openAdminBtn) {
    openAdminBtn.addEventListener("click", handleOpenAdminClick);
  }

  // Input Box & Send
  if (promptInput) {
    promptInput.addEventListener("input", () => {
      const hasText = promptInput.value.trim().length > 0;
      if (sendBtn) {
        if (hasText) {
          sendBtn.classList.add("active");
        } else {
          sendBtn.classList.remove("active");
        }
      }
    });

    promptInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendPrompt();
      }
    });
  }

  if (sendBtn) {
    sendBtn.addEventListener("click", handleSendPrompt);
  }

  // Kartu Saran Prompt
  document.querySelectorAll(".suggestion-card").forEach(card => {
    card.addEventListener("click", () => {
      const text = card.getAttribute("data-prompt") || (card.querySelector(".card-text") ? card.querySelector(".card-text").innerText.trim() : "");
      selectSuggestion(text);
    });
  });

  // Voice Input (Speech Recognition)
  if (micBtn) {
    micBtn.addEventListener("click", toggleVoiceRecognition);
  }

  // Admin Modal Close & Tools
  if (closeAdminBtn) {
    closeAdminBtn.addEventListener("click", closeAdminModal);
  }

  if (adminSearchInput) {
    let debounceTimer;
    adminSearchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadAdminLogs(adminSearchInput.value.trim());
      }, 300);
    });
  }

  if (btnCleanOld) {
    btnCleanOld.addEventListener("click", cleanOldLogs);
  }

  if (btnWipeAll) {
    btnWipeAll.addEventListener("click", wipeAllLogs);
  }
}

function handleRoleBadgeClick() {
  if (isAdmin) {
    openAdminModal();
  } else {
    alert("Akun Anda saat ini masuk sebagai Pengguna biasa ('" + (currentUser ? currentUser.username : "User") + "'). Fitur Admin hanya dapat diakses oleh akun berstatus Administrator.");
  }
}
window.handleRoleBadgeClick = handleRoleBadgeClick;

function handleOpenAdminClick() {
  closeMobileSidebar();
  if (isAdmin) {
    openAdminModal();
  } else {
    alert("Akses ditolak: Hanya Administrator yang dapat membuka menu ini.");
  }
}
window.handleOpenAdminClick = handleOpenAdminClick;

function selectSuggestion(text) {
  if (!text) return;
  const input = document.getElementById("promptInput");
  if (input) {
    input.value = text;
    input.dispatchEvent(new Event("input"));
    handleSendPrompt();
  }
}
window.selectSuggestion = selectSuggestion;

function openAdminModal() {
  const modal = document.getElementById("adminModal");
  if (modal) {
    modal.classList.add("open", "active");
    modal.style.display = "flex";
  }
  switchAdminTab("storage");
}
window.openAdminModal = openAdminModal;

function closeAdminModal() {
  const modal = document.getElementById("adminModal");
  if (modal) {
    modal.classList.remove("open", "active");
    modal.style.display = "none";
  }
}
window.closeAdminModal = closeAdminModal;

// ==========================================
// ADMIN TAB SWITCHER & USER MANAGEMENT
// ==========================================

function switchAdminTab(tab) {
  const tabBtnStorage = document.getElementById("tabBtnStorage");
  const tabBtnUsers = document.getElementById("tabBtnUsers");
  const paneStorage = document.getElementById("paneStorage");
  const paneUsers = document.getElementById("paneUsers");

  if (tab === "storage") {
    if (tabBtnStorage) tabBtnStorage.classList.add("active");
    if (tabBtnUsers) tabBtnUsers.classList.remove("active");
    if (paneStorage) paneStorage.style.display = "block";
    if (paneUsers) paneUsers.style.display = "none";
    loadAdminStats();
    loadAdminLogs(adminSearchInput ? adminSearchInput.value.trim() : "");
  } else {
    if (tabBtnUsers) tabBtnUsers.classList.add("active");
    if (tabBtnStorage) tabBtnStorage.classList.remove("active");
    if (paneUsers) paneUsers.style.display = "block";
    if (paneStorage) paneStorage.style.display = "none";
    loadAdminUsers();
  }
}
window.switchAdminTab = switchAdminTab;

async function loadAdminUsers() {
  const tbody = document.getElementById("adminUsersTableBody");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-muted);">Memuat daftar akun...</td></tr>`;

  try {
    const res = await fetch(`/api/admin/users?secret_key=${encodeURIComponent(adminSecretKey)}`);
    if (!res.ok) throw new Error("Gagal mengambil data pengguna.");
    const data = await res.json();
    const users = data.users || [];

    tbody.innerHTML = "";
    if (users.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-muted);">Belum ada user terdaftar.</td></tr>`;
      return;
    }

    users.forEach(u => {
      const tr = document.createElement("tr");
      const isMainAdmin = u.username.toLowerCase() === "admin";
      const isSelf = currentUser && u.username.toLowerCase() === currentUser.username.toLowerCase();
      const isActive = u.status === "active";
      const statusBadgeHtml = isActive
        ? `<span class="status-badge active"><svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"></circle></svg> Aktif</span>`
        : `<span class="status-badge inactive"><svg width="8" height="8" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"></circle></svg> Nonaktif</span>`;

      const roleBadgeHtml = u.role === "admin"
        ? `<span class="role-tag" style="background:#fef7e0; color:#b06000; border: 1px solid #fce8b2; font-weight:600;">👑 Admin</span>`
        : `<span class="role-tag" style="background:#e8f0fe; color:#1a73e8; border: 1px solid #d2e3fc; font-weight:500;">👤 User</span>`;

      const dateStr = u.created_at ? new Date(u.created_at).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "-";

      let actionsHtml = "";
      if (isMainAdmin) {
        actionsHtml = `<span style="font-size: 11.5px; color: var(--text-muted); font-style: italic;">Admin Utama</span>`;
      } else if (isSelf) {
        actionsHtml = `<span style="font-size: 11.5px; color: var(--text-muted); font-style: italic;">Akun Anda</span>`;
      } else {
        const toggleBtnText = isActive ? "Nonaktifkan Sementara" : "Aktifkan Kembali";
        const toggleBtnClass = isActive ? "deactivate" : "activate";
        const toggleTargetStatus = isActive ? "inactive" : "active";

        actionsHtml = `
          <div style="display: flex; gap: 6px; justify-content: center; align-items: center;">
            <button class="btn-toggle-status ${toggleBtnClass}" onclick="window.handleToggleUserStatus('${escapeHtml(u.username)}', '${toggleTargetStatus}')" title="${isActive ? 'Nonaktifkan sementara agar user tidak bisa login' : 'Aktifkan kembali agar user bisa login'}">
              ${toggleBtnText}
            </button>
            <button class="btn-action-delete" onclick="window.handleDeleteUser('${escapeHtml(u.username)}')" title="Hapus pengguna permanen">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            </button>
          </div>
        `;
      }

      tr.innerHTML = `
        <td style="font-weight: 600; color: var(--text-primary); font-size: 13.5px;">${escapeHtml(u.username)}</td>
        <td>${roleBadgeHtml}</td>
        <td>${statusBadgeHtml}</td>
        <td style="font-size: 12px; color: var(--text-muted);">${dateStr}</td>
        <td style="text-align: center;">${actionsHtml}</td>
      `;

      tbody.appendChild(tr);
    });

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--danger);">Gagal memuat pengguna: ${escapeHtml(err.message)}</td></tr>`;
  }
}
window.loadAdminUsers = loadAdminUsers;

async function handleAddUserSubmit(event) {
  if (event) event.preventDefault();
  const uInput = document.getElementById("newUsernameInput");
  const pInput = document.getElementById("newPasswordInput");
  const rSelect = document.getElementById("newUserRoleSelect");
  const msgDiv = document.getElementById("addUserMsg");
  const submitBtn = document.getElementById("submitNewUserBtn");

  const username = uInput ? uInput.value.trim() : "";
  const password = pInput ? pInput.value.trim() : "";
  const role = rSelect ? rSelect.value : "user";

  if (!username || !password) {
    if (msgDiv) {
      msgDiv.style.color = "var(--danger)";
      msgDiv.innerText = "Username dan password wajib diisi.";
      msgDiv.style.display = "block";
    }
    return;
  }

  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch(`/api/admin/users?secret_key=${encodeURIComponent(adminSecretKey)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, role })
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      throw new Error(data.detail || "Gagal menambahkan pengguna.");
    }

    if (msgDiv) {
      msgDiv.style.color = "var(--success)";
      msgDiv.innerText = `Pengguna '${username}' berhasil ditambahkan (Status: Aktif)!`;
      msgDiv.style.display = "block";
    }

    if (uInput) uInput.value = "";
    if (pInput) pInput.value = "";

    loadAdminUsers();
    setTimeout(() => {
      if (msgDiv) msgDiv.style.display = "none";
    }, 4000);

  } catch (err) {
    if (msgDiv) {
      msgDiv.style.color = "var(--danger)";
      msgDiv.innerText = err.message;
      msgDiv.style.display = "block";
    }
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}
window.handleAddUserSubmit = handleAddUserSubmit;

async function handleToggleUserStatus(username, newStatus) {
  const actionText = newStatus === "inactive" ? "menonaktifkan sementara" : "mengaktifkan kembali";
  if (!confirm(`Apakah Anda yakin ingin ${actionText} akun '${username}'?`)) return;

  try {
    const res = await fetch(`/api/admin/users/${encodeURIComponent(username)}/status?secret_key=${encodeURIComponent(adminSecretKey)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      throw new Error(data.detail || "Gagal mengubah status pengguna.");
    }

    loadAdminUsers();
  } catch (err) {
    alert("Error: " + err.message);
  }
}
window.handleToggleUserStatus = handleToggleUserStatus;

async function handleDeleteUser(username) {
  if (!confirm(`PERINGATAN: Apakah Anda yakin ingin menghapus akun '${username}' secara permanen? Tindakan ini tidak dapat dibatalkan.`)) return;

  try {
    const res = await fetch(`/api/admin/users/${encodeURIComponent(username)}?secret_key=${encodeURIComponent(adminSecretKey)}`, {
      method: "DELETE"
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      throw new Error(data.detail || "Gagal menghapus pengguna.");
    }

    loadAdminUsers();
  } catch (err) {
    alert("Error: " + err.message);
  }
}
window.handleDeleteUser = handleDeleteUser;

function setupTextareaAutoResize() {
  const pInput = document.getElementById("promptInput");
  if (pInput) {
    pInput.addEventListener("input", function() {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 200) + "px";
    });
  }
}

function showHero() {
  initDomReferences();
  if (heroGreeting) heroGreeting.style.display = "block";
  if (messagesList) messagesList.innerHTML = "";
}

function hideHero() {
  initDomReferences();
  if (heroGreeting) heroGreeting.style.display = "none";
}

function scrollToBottom() {
  initDomReferences();
  if (chatScrollArea) chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
}

// ==========================================
// SESSION MANAGEMENT
// ==========================================

async function loadSessions() {
  try {
    const res = await fetch("/api/sessions");
    const data = await res.json();
    renderSessionsList(data.sessions || []);
  } catch (err) {
    console.error("Gagal memuat sesi:", err);
  }
}

function renderSessionsList(sessions) {
  initDomReferences();
  if (!sessionsList) return;
  sessionsList.innerHTML = "";

  // Filter sesi: Pengguna biasa hanya melihat sesi milik sendiri di perangkat ini
  // Admin dapat melihat seluruh sesi
  const myIds = getMySessionIds();
  const displaySessions = isAdmin ? sessions : sessions.filter(s => myIds.includes(s.id));

  if (displaySessions.length === 0) {
    sessionsList.innerHTML = `<div style="padding: 10px 14px; font-size: 12px; color: var(--text-muted);">Belum ada riwayat</div>`;
    return;
  }

  displaySessions.forEach(s => {
    const item = document.createElement("div");
    item.className = `session-item ${s.id === currentSessionId ? "active" : ""}`;
    item.innerHTML = `
      <span class="session-title" title="${escapeHtml(s.title)}">${escapeHtml(s.title)}</span>
      <button class="session-delete-btn" title="Hapus riwayat">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
      </button>
    `;

    item.addEventListener("click", (e) => {
      if (e.target.closest(".session-delete-btn")) return;
      selectSession(s.id);
    });

    const delBtn = item.querySelector(".session-delete-btn");
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteSession(s.id);
    });

    sessionsList.appendChild(item);
  });
}

function startNewChat() {
  initDomReferences();
  currentSessionId = null;
  localStorage.removeItem("gemini_current_session");
  showHero();
  loadSessions();
  if (promptInput) {
    promptInput.value = "";
    promptInput.focus();
  }
}

async function selectSession(sessionId) {
  closeMobileSidebar();
  currentSessionId = sessionId;
  localStorage.setItem("gemini_current_session", sessionId);
  loadSessions();
  loadSessionMessages(sessionId);
}

async function loadSessionMessages(sessionId) {
  try {
    const res = await fetch(`/api/sessions/${sessionId}`);
    const data = await res.json();
    hideHero();
    messagesList.innerHTML = "";
    
    if (data.messages && data.messages.length > 0) {
      data.messages.forEach(msg => {
        if (msg.role === "user") {
          appendUserMessage(msg.content);
        } else {
          appendModelMessage(msg.content, msg.id, false, msg.storage_bytes);
        }
      });
      scrollToBottom();
    } else {
      showHero();
    }
  } catch (err) {
    console.error("Gagal mengambil pesan:", err);
  }
}

async function deleteSession(sessionId) {
  if (!confirm("Hapus seluruh percakapan ini beserta data di database?")) return;
  try {
    await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
    if (currentSessionId === sessionId) {
      startNewChat();
    } else {
      loadSessions();
    }
  } catch (err) {
    console.error("Gagal menghapus sesi:", err);
  }
}

// ==========================================
// CHAT & STREAMING LOGIC
// ==========================================

async function handleSendPrompt() {
  initDomReferences();
  if (!promptInput) return;
  const prompt = promptInput.value.trim();
  if (!prompt || isGenerating) return;

  isGenerating = true;
  hideHero();

  // Bersihkan input box
  promptInput.value = "";
  promptInput.style.height = "auto";
  if (sendBtn) sendBtn.classList.remove("active");

  // Jika belum ada sesi, buat ID acak di frontend
  if (!currentSessionId) {
    currentSessionId = "session-" + Math.random().toString(36).substring(2, 11) + "-" + Date.now();
    localStorage.setItem("gemini_current_session", currentSessionId);
  }
  addMySessionId(currentSessionId);

  // 1. Tampilkan bubble pesan user di layar
  appendUserMessage(prompt);

  // 2. Buat placeholder bubble model dengan indikator streaming cursor
  const modelMessageElement = appendModelMessage("", null, true);
  if (!modelMessageElement) {
    isGenerating = false;
    return;
  }
  const responseContentDiv = modelMessageElement.querySelector(".model-response-body");
  const actionsDiv = modelMessageElement.querySelector(".message-actions");

  scrollToBottom();

  let accumulatedText = "";
  let modelMsgId = null;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        prompt: prompt,
        model: "gemini-3.6-flash"
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // simpan sisa baris belum lengkap

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("data: ")) {
          const jsonStr = trimmed.substring(6).trim();
          if (!jsonStr) continue;

          try {
            const eventData = JSON.parse(jsonStr);

            if (eventData.type === "start") {
              modelMsgId = eventData.model_msg_id;
              modelMessageElement.setAttribute("data-msg-id", modelMsgId);
            } else if (eventData.type === "chunk") {
              accumulatedText += eventData.text;
              if (responseContentDiv) renderMarkdownLive(responseContentDiv, accumulatedText, true);
              scrollToBottom();
            } else if (eventData.type === "done") {
              const bytesUsed = eventData.bytes || accumulatedText.length;
              if (responseContentDiv) renderMarkdownLive(responseContentDiv, accumulatedText, false);
              if (actionsDiv) showModelActions(actionsDiv, accumulatedText, bytesUsed);
              loadSessions(); // refresh title di sidebar
            } else if (eventData.type === "error") {
              accumulatedText += `\n\n❌ *Error*: ${eventData.message}`;
              if (responseContentDiv) renderMarkdownLive(responseContentDiv, accumulatedText, false);
            }
          } catch (pe) {
            console.error("Gagal parse SSE:", pe);
          }
        }
      }
    }

    // Jika stream selesai tanpa event done eksplisit
    if (responseContentDiv) renderMarkdownLive(responseContentDiv, accumulatedText, false);
    if (actionsDiv) showModelActions(actionsDiv, accumulatedText, accumulatedText.length);

  } catch (err) {
    console.error("Error streaming:", err);
    if (responseContentDiv) {
      responseContentDiv.innerHTML = `<p style="color: var(--danger);">Gagal mengirim pesan: ${escapeHtml(err.message)}</p>`;
    }
  } finally {
    isGenerating = false;
    scrollToBottom();
  }
}

function appendUserMessage(text) {
  initDomReferences();
  if (!messagesList) return null;
  const row = document.createElement("div");
  row.className = "message-row user";
  row.innerHTML = `<div class="user-bubble message-bubble">${escapeHtml(text)}</div>`;
  messagesList.appendChild(row);
  scrollToBottom();
  return row;
}

function appendModelMessage(text = "", messageId = null, isLive = false, bytes = 0) {
  initDomReferences();
  if (!messagesList) return null;
  const row = document.createElement("div");
  row.className = "message-row model";
  if (messageId) row.setAttribute("data-msg-id", messageId);

  row.innerHTML = `
    <div class="model-avatar-container message-avatar-container">
      <img src="/static/images/mascot.png" class="model-avatar-img message-avatar-img" alt="Cipuy Avatar">
    </div>
    <div class="model-content-wrapper" style="flex: 1; min-width: 0; overflow: hidden;">
      <div class="model-response-body message-bubble"></div>
      <div class="message-actions" style="display: none;"></div>
    </div>
  `;

  const bodyDiv = row.querySelector(".model-response-body");
  const actionsDiv = row.querySelector(".message-actions");

  if (text) {
    renderMarkdownLive(bodyDiv, text, false);
    showModelActions(actionsDiv, text, bytes || text.length);
  } else if (isLive) {
    bodyDiv.innerHTML = `<span class="typing-cursor"></span>`;
  }

  messagesList.appendChild(row);
  return row;
}

function renderMarkdownLive(container, rawText, isStreaming) {
  let parsedHtml = "";
  if (window.marked) {
    try {
      parsedHtml = marked.parse(rawText);
    } catch (e) {
      parsedHtml = `<p>${escapeHtml(rawText)}</p>`;
    }
  } else {
    parsedHtml = `<p>${escapeHtml(rawText)}</p>`;
  }

  if (isStreaming) {
    parsedHtml += `<span class="typing-cursor"></span>`;
  }

  container.innerHTML = parsedHtml;

  // Pasang tombol Copy Code di setiap blok <pre><code>
  container.querySelectorAll("pre").forEach(pre => {
    if (pre.parentNode.classList.contains("code-wrapper")) return;

    const wrapper = document.createElement("div");
    wrapper.className = "code-wrapper";

    const code = pre.querySelector("code");
    const lang = code ? (code.className.replace("language-", "") || "code") : "code";

    const header = document.createElement("div");
    header.className = "code-header";
    header.innerHTML = `
      <span>${lang}</span>
      <button class="btn-copy-code">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        <span>Salin kode</span>
      </button>
    `;

    const copyBtn = header.querySelector(".btn-copy-code");
    copyBtn.addEventListener("click", () => {
      const codeText = code ? code.innerText : pre.innerText;
      navigator.clipboard.writeText(codeText);
      copyBtn.querySelector("span").innerText = "Tersalin!";
      setTimeout(() => {
        copyBtn.querySelector("span").innerText = "Salin kode";
      }, 2000);
    });

    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(header);
    wrapper.appendChild(pre);
  });
}

function showModelActions(actionsDiv, fullText, bytes) {
  actionsDiv.style.display = "flex";
  const kbFormatted = (bytes / 1024).toFixed(2);

  actionsDiv.innerHTML = `
    <button class="action-btn btn-copy-response" title="Salin Jawaban">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
    </button>
    <button class="action-btn" title="Bagus">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>
    </button>
    <div class="storage-badge" title="Tersimpan di Cloud Database">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
      <span>${kbFormatted} KB tersimpan di DB</span>
    </div>
  `;

  const copyBtn = actionsDiv.querySelector(".btn-copy-response");
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(fullText);
    copyBtn.style.color = "var(--accent-blue)";
    setTimeout(() => { copyBtn.style.color = ""; }, 1500);
  });
}

// ==========================================
// VOICE RECOGNITION (MIC)
// ==========================================

function toggleVoiceRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("Browser Anda belum mendukung fitur Speech-to-Text bawaan.");
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = "id-ID";
  recognition.interimResults = false;

  micBtn.style.color = "var(--danger)";

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    promptInput.value = (promptInput.value ? promptInput.value + " " : "") + transcript;
    promptInput.dispatchEvent(new Event("input"));
    micBtn.style.color = "";
  };

  recognition.onerror = () => {
    micBtn.style.color = "";
  };

  recognition.onend = () => {
    micBtn.style.color = "";
  };

  recognition.start();
}

// ==========================================
// ADMIN DASHBOARD & STORAGE MANAGER
// ==========================================

async function loadAdminStats() {
  try {
    const url = `/api/admin/stats?secret_key=${encodeURIComponent(adminSecretKey)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Gagal otorisasi admin.");
    const s = await res.json();

    const statEngine = document.getElementById("statEngine");
    const statSessions = document.getElementById("statSessions");
    const statPrompts = document.getElementById("statPrompts");
    const statResponses = document.getElementById("statResponses");
    const statStorageMb = document.getElementById("statStorageMb");
    const statUsagePercent = document.getElementById("statUsagePercent");
    const fillBar = document.getElementById("storageProgressFill");

    if (statEngine) statEngine.innerText = s.db_engine;
    if (statSessions) statSessions.innerText = s.total_sessions;
    if (statPrompts) statPrompts.innerText = s.total_user_prompts;
    if (statResponses) statResponses.innerText = s.total_ai_responses;
    if (statStorageMb) statStorageMb.innerText = s.storage_mb + " MB";
    if (statUsagePercent) statUsagePercent.innerText = s.usage_percentage + "%";
    if (fillBar) fillBar.style.width = Math.min(Math.max(s.usage_percentage, 0.5), 100) + "%";
  } catch (err) {
    console.error("Admin stats error:", err);
  }
}
window.loadAdminStats = loadAdminStats;

async function loadAdminLogs(query = "") {
  try {
    const tbody = document.getElementById("adminLogsTableBody");
    if (!tbody) return;

    const url = `/api/admin/logs?secret_key=${encodeURIComponent(adminSecretKey)}&query=${encodeURIComponent(query)}&limit=50`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Gagal mengambil log.");
    const data = await res.json();

    tbody.innerHTML = "";
    if (!data.logs || data.logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 20px;">Belum ada riwayat percakapan yang tercatat.</td></tr>`;
      return;
    }

    data.logs.forEach(log => {
      const tr = document.createElement("tr");
      const dateStr = log.created_at ? new Date(log.created_at).toLocaleString("id-ID") : "-";
      const sizeKb = (log.storage_bytes / 1024).toFixed(2);

      tr.innerHTML = `
        <td style="font-size: 11px; font-family: monospace;">${log.id.substring(0, 8)}...</td>
        <td style="font-size: 12px;">${dateStr}</td>
        <td><span class="role-tag ${log.role}">${log.role === "user" ? "User Prompt" : "Cipuy AI"}</span></td>
        <td style="max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(log.content)}">
          ${escapeHtml(log.content.substring(0, 75))}${log.content.length > 75 ? "..." : ""}
        </td>
        <td><span class="status-tag ${log.status}">${log.status}</span></td>
        <td style="font-size: 12px;">${sizeKb} KB</td>
        <td style="text-align: center;">
          <button class="btn-del-sm" title="Hapus pesan ini dari database">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </td>
      `;

      const delBtn = tr.querySelector(".btn-del-sm");
      delBtn.addEventListener("click", () => deleteLogMessage(log.id));

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Admin logs error:", err);
  }
}
window.loadAdminLogs = loadAdminLogs;

async function deleteLogMessage(messageId) {
  if (!confirm("Hapus baris data pencarian/respons ini dari database untuk menghemat storage?")) return;
  try {
    const res = await fetch(`/api/admin/logs/${messageId}?secret_key=${encodeURIComponent(adminSecretKey)}`, {
      method: "DELETE"
    });
    if (res.ok) {
      loadAdminStats();
      loadAdminLogs(adminSearchInput ? adminSearchInput.value.trim() : "");
    }
  } catch (err) {
    alert("Gagal menghapus data: " + err.message);
  }
}

async function cleanOldLogs() {
  const days = prompt("Hapus log pencarian yang lebih lama dari berapa hari?", "14");
  if (!days) return;

  try {
    const res = await fetch("/api/admin/clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        secret_key: adminSecretKey,
        days: parseInt(days),
        wipe_all: false
      })
    });
    const data = await res.json();
    alert(data.message || "Pembersihan berhasil.");
    loadAdminStats();
    loadAdminLogs();
  } catch (err) {
    alert("Gagal membersihkan database: " + err.message);
  }
}

async function wipeAllLogs() {
  const confirmWipe = prompt("PERINGATAN: Tindakan ini akan mengosongkan SEMUA pesan dan sesi di database. Ketik 'BERSIHKAN' untuk melanjutkan:");
  if (confirmWipe !== "BERSIHKAN") return;

  try {
    const res = await fetch("/api/admin/clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        secret_key: adminSecretKey,
        wipe_all: true
      })
    });
    const data = await res.json();
    alert(data.message || "Database telah dikosongkan total.");
    startNewChat();
    loadAdminStats();
    loadAdminLogs();
  } catch (err) {
    alert("Gagal mengosongkan database: " + err.message);
  }
}

// Helper untuk escape HTML
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Window global bindings agar aman dipanggil via onclick di HTML (HP & Desktop)
window.startNewChat = startNewChat;
window.handleNewChat = handleNewChat;
window.handleSendPrompt = handleSendPrompt;
window.toggleVoiceRecognition = toggleVoiceRecognition;
window.cleanOldLogs = cleanOldLogs;
window.wipeAllLogs = wipeAllLogs;
window.openAdminModal = openAdminModal;
window.closeAdminModal = closeAdminModal;
window.switchAdminTab = switchAdminTab;
window.loadAdminUsers = loadAdminUsers;
window.handleAddUserSubmit = handleAddUserSubmit;
window.handleToggleUserStatus = handleToggleUserStatus;
window.handleDeleteUser = handleDeleteUser;
window.handleRoleBadgeClick = handleRoleBadgeClick;
window.handleOpenAdminClick = handleOpenAdminClick;
window.openMobileSidebar = openMobileSidebar;
window.closeMobileSidebar = closeMobileSidebar;
window.toggleSidebar = toggleSidebar;
window.selectSuggestion = selectSuggestion;
window.handleGateLoginSubmit = handleGateLoginSubmit;
window.handleLogout = handleLogout;
window.loadAdminStats = loadAdminStats;
window.loadAdminLogs = loadAdminLogs;

