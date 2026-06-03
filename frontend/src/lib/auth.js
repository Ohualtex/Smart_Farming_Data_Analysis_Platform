import { api, apiAuth, setAuthToken, clearAuthToken } from "./api.js";
import { showToast } from "./ui_helpers.js";

// state variable
export let currentUser = null;
export function setCurrentUser(user) {
    currentUser = user;
}
export let apiOnline = true;

// Rol → kullanıcı dostu Türkçe etiket
const ROLE_LABELS = {
    farmer: 'çiftçi',
    developer: 'geliştirici',
    overseer: 'gözetmen',
    admin: 'yönetici',
};

/**
 * Header user badge'ini doldur veya gizle. `user` null ise badge gizlenir
 * (anonim akış). Login/logout sonrası ve refreshAuthState içinde çağırılır.
 */
function _renderUserBadge(user) {
    const badge = document.getElementById('userBadge');
    if (!badge) return;
    if (!user) {
        badge.style.display = 'none';
        return;
    }
    badge.style.display = 'inline-flex';
    document.getElementById('userBadgeName').textContent = user.name || 'kullanıcı';
    const roleEl = document.getElementById('userBadgeRole');
    roleEl.textContent = ROLE_LABELS[user.role] || user.role;
    roleEl.dataset.role = user.role;
    const farmCount = user.owned_farms_count ?? 0;
    document.getElementById('userBadgeFarms').textContent = `🚜 ${farmCount}`;
}

/**
 * Auth gate — REBUILD Faz 3.5. `user` varsa app shell'i göster + landing'i gizle;
 * yoksa tersi. Tek kaynak: refreshAuthState her durumda çağırır.
 */
function _applyAuthGate(user) {
    const landing = document.getElementById('landing');
    const app = document.querySelector('.app');
    if (!landing || !app) return;
    if (user) {
        landing.style.display = 'none';
        app.style.display = '';  // flex (CSS default)
    } else {
        landing.style.display = 'flex';
        app.style.display = 'none';
    }
}

/**
 * Rol-aware nav görünürlüğü — `[data-role]` taşıyan nav item'ları yalnız
 * eşleşen role gösterir (örn. admin "Kullanıcılar"). user null ise hepsi gizli.
 */
function _applyRoleVisibility(user) {
    document.querySelectorAll('[data-role]').forEach(el => {
        // data-role tek rol ("admin") veya virgüllü çoklu rol ("admin,overseer,developer")
        const roles = (el.getAttribute('data-role') || '').split(',').map(r => r.trim());
        el.style.display = (user && roles.includes(user.role)) ? '' : 'none';
    });
}

/** Landing'de giriş ↔ kayıt formu geçişi. */
export function toggleLandingForm(which) {
    const login = document.getElementById('landingLogin');
    const register = document.getElementById('landingRegister');
    if (!login || !register) return;
    login.style.display = which === 'register' ? 'none' : 'block';
    register.style.display = which === 'register' ? 'block' : 'none';
}

export async function refreshAuthState() {
    const token = getAuthToken();
    const loggedIn = document.getElementById('authLoggedIn');
    if (!token) {
        currentUser = null;
        _renderUserBadge(null);
        _applyRoleVisibility(null);
        _applyAuthGate(null);
        window.dispatchEvent(new CustomEvent('hideBell'));
        return;
    }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!resp.ok) { clearAuthToken(); refreshAuthState(); return; }
        const me = await resp.json();
        currentUser = me;
        _renderUserBadge(me);
        _applyRoleVisibility(me);
        _applyAuthGate(me);
        refreshBell();
        // Hesabım sayfası alanları — null-safe (page-auth artık yalnız logged-in).
        const nameEl = document.getElementById('authName');
        if (nameEl) nameEl.textContent = me.name;
        const emailEl = document.getElementById('authEmail');
        if (emailEl) emailEl.textContent = me.email;
        const roleEl = document.getElementById('authRole');
        if (roleEl) roleEl.textContent = ROLE_LABELS[me.role] || me.role;
        const phoneEl = document.getElementById('authPhone');
        if (phoneEl) phoneEl.textContent = me.phone || '—';
        const farmsEl = document.getElementById('authOwnedFarms');
        if (farmsEl) farmsEl.textContent = me.owned_farms_count ?? 0;
        if (loggedIn) loggedIn.style.display = 'block';
    } catch (e) {
        currentUser = null;
        _renderUserBadge(null);
        _applyRoleVisibility(null);
        _applyAuthGate(null);
        window.dispatchEvent(new CustomEvent('hideBell'));
    }
}
