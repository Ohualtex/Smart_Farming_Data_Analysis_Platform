import { api, apiAuth, API_BASE, getAuthToken, setAuthToken, clearAuthToken } from "./api.js";
import { showToast, clearAllErrors, setFieldError } from "./ui_helpers.js";

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
        window.dispatchEvent(new CustomEvent('refreshBell'));
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

export async function doLogin() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    clearAllErrors('loginEmail', 'loginPassword');
    let hasError = false;
    if (!email) { setFieldError('loginEmail', 'E-posta gerekli.'); hasError = true; }
    if (!password) { setFieldError('loginPassword', 'Şifre gerekli.'); hasError = true; }
    if (hasError) { showToast('Lütfen eksik alanları doldur.', 'warning'); return; }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            showToast(err.detail || 'Giriş başarısız', 'error');
            return;
        }
        const data = await resp.json();
        setAuthToken(data.access_token);
        showToast('Giriş yapıldı', 'success');
        await refreshAuthState();
        window.dispatchEvent(new CustomEvent('navigate', { detail: 'dashboard' }));
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    }
}

export async function doRegister() {
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;
    clearAllErrors('regName', 'regEmail', 'regPassword');
    let hasError = false;
    if (!name) { setFieldError('regName', 'Ad gerekli.'); hasError = true; }
    if (!email) { setFieldError('regEmail', 'E-posta gerekli.'); hasError = true; }
    if (!password) {
        setFieldError('regPassword', 'Şifre gerekli.');
        hasError = true;
    } else if (password.length < 8) {
        setFieldError('regPassword', 'Şifre en az 8 karakter olmalı.');
        hasError = true;
    }
    if (hasError) { showToast('Lütfen formu kontrol et.', 'warning'); return; }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            showToast(err.detail || 'Kayıt başarısız', 'error');
            return;
        }
        showToast('Hesap oluşturuldu, giriş yapabilirsin', 'success');
        document.getElementById('loginEmail').value = email;
        document.getElementById('loginPassword').value = password;
        doLogin();
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    }
}

export async function doChangePassword() {
    const current = document.getElementById('pwCurrent').value;
    const next = document.getElementById('pwNew').value;
    const confirm_ = document.getElementById('pwConfirm').value;
    if (!current || !next || !confirm_) {
        showToast('Tüm alanlar gerekli', 'warning');
        return;
    }
    if (next.length < 8) {
        showToast('Yeni şifre en az 8 karakter olmalı', 'warning');
        return;
    }
    if (next !== confirm_) {
        showToast('Yeni şifreler eşleşmiyor', 'warning');
        return;
    }
    if (next === current) {
        showToast('Yeni şifre mevcuttan farklı olmalı', 'warning');
        return;
    }
    const token = getAuthToken();
    if (!token) {
        showToast('Giriş yapman gerekiyor', 'warning');
        location.hash = '#auth';
        return;
    }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/me/password`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify({ current_password: current, new_password: next }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            showToast(err.detail || 'Şifre güncellenemedi', 'error');
            return;
        }
        showToast('Şifre güncellendi ✅', 'success');
        document.getElementById('pwCurrent').value = '';
        document.getElementById('pwNew').value = '';
        document.getElementById('pwConfirm').value = '';
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    }
}

export function doLogout() {
    const token = getAuthToken();
    if (token) {
        try {
            fetch(`${API_BASE}/api/auth/logout`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });
        } catch (e) { /* ignore */ }
    }
    clearAuthToken();
    currentUser = null;
    _renderUserBadge(null);
    _applyRoleVisibility(null);
    _applyAuthGate(null);
    window.dispatchEvent(new CustomEvent('hideBell'));
    showToast('Çıkış yapıldı', 'info');
    window.dispatchEvent(new CustomEvent('navigate', { detail: 'auth' }));
}
