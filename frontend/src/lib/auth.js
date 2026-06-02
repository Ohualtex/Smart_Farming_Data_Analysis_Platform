import { API_BASE, getAuthToken, setAuthToken, clearAuthToken } from "./api.js";
import { clearAllErrors, setFieldError } from "./ui_helpers.js";

export let currentUser = null;

export const ROLE_LABELS = {
    farmer: 'çiftçi',
    developer: 'geliştirici',
    overseer: 'gözetmen',
    admin: 'yönetici',
};

export function getCurrentUser() {
    return currentUser;
}

export function _renderUserBadge(user) {
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

export function _applyAuthGate(user) {
    const landing = document.getElementById('landing');
    const app = document.querySelector('.app');
    if (!landing || !app) return;
    if (user) {
        landing.style.display = 'none';
        app.style.display = '';
    } else {
        landing.style.display = 'flex';
        app.style.display = 'none';
    }
}

export function _applyRoleVisibility(user) {
    document.querySelectorAll('[data-role]').forEach(el => {
        const roles = (el.getAttribute('data-role') || '').split(',').map(r => r.trim());
        el.style.display = (user && roles.includes(user.role)) ? '' : 'none';
    });
}

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
        window.dispatchEvent(new CustomEvent('auth-status-changed', { detail: null }));
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

        window.dispatchEvent(new CustomEvent('auth-status-changed', { detail: me }));
    } catch (e) {
        currentUser = null;
        _renderUserBadge(null);
        _applyRoleVisibility(null);
        _applyAuthGate(null);
        window.dispatchEvent(new CustomEvent('auth-status-changed', { detail: null }));
    }
}

export async function doLogin() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    clearAllErrors('loginEmail', 'loginPassword');
    let hasError = false;
    if (!email) { setFieldError('loginEmail', 'E-posta gerekli.'); hasError = true; }
    if (!password) { setFieldError('loginPassword', 'Şifre gerekli.'); hasError = true; }
    if (hasError) { window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Lütfen eksik alanları doldur.', type: 'warning' } })); return; }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            window.dispatchEvent(new CustomEvent('toast', { detail: { msg: err.detail || 'Giriş başarısız', type: 'error' } }));
            return;
        }
        const data = await resp.json();
        setAuthToken(data.access_token);
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Giriş yapıldı', type: 'success' } }));
        await refreshAuthState();
        window.dispatchEvent(new CustomEvent('navigate', { detail: 'dashboard' }));
    } catch (e) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Sunucuya ulaşılamadı', type: 'error' } }));
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
    if (hasError) { window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Lütfen formu kontrol et.', type: 'warning' } })); return; }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            window.dispatchEvent(new CustomEvent('toast', { detail: { msg: err.detail || 'Kayıt başarısız', type: 'error' } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Hesap oluşturuldu, giriş yapabilirsin', type: 'success' } }));
        document.getElementById('loginEmail').value = email;
        document.getElementById('loginPassword').value = password;
        doLogin();
    } catch (e) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Sunucuya ulaşılamadı', type: 'error' } }));
    }
}

export async function doChangePassword() {
    const current = document.getElementById('pwCurrent').value;
    const next = document.getElementById('pwNew').value;
    const confirm = document.getElementById('pwConfirm').value;
    if (!current || !next || !confirm) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Tüm alanlar gerekli', type: 'warning' } }));
        return;
    }
    if (next.length < 8) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Yeni şifre en az 8 karakter olmalı', type: 'warning' } }));
        return;
    }
    if (next !== confirm) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Yeni şifreler eşleşmiyor', type: 'warning' } }));
        return;
    }
    if (next === current) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Yeni şifre mevcuttan farklı olmalı', type: 'warning' } }));
        return;
    }
    const token = getAuthToken();
    if (!token) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Giriş yapman gerekiyor', type: 'warning' } }));
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
            window.dispatchEvent(new CustomEvent('toast', { detail: { msg: err.detail || 'Şifre güncellenemedi', type: 'error' } }));
            return;
        }
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Şifre güncellendi ✅', type: 'success' } }));
        document.getElementById('pwCurrent').value = '';
        document.getElementById('pwNew').value = '';
        document.getElementById('pwConfirm').value = '';
    } catch (e) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Sunucuya ulaşılamadı', type: 'error' } }));
    }
}

export async function doLogout() {
    const token = getAuthToken();
    if (token) {
        try {
            await fetch(`${API_BASE}/api/auth/logout`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });
        } catch (e) { /* ignore */ }
    }
    clearAuthToken();
    window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Çıkış yapıldı', type: 'info' } }));
    await refreshAuthState();
    toggleLandingForm('login');
    if (location.hash) location.hash = '';
}
