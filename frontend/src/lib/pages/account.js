/* ============================================================
   SFDAP — Account / Auth + Admin Users Module
   ============================================================
   Giriş/kayıt/çıkış/şifre, auth gate + rol görünürlüğü, header
   user badge, refreshAuthState ve admin kullanıcı yönetimi.
   ROLE_LABELS burada tek kaynak (loadUsers + badge ortak kullanır).
   ============================================================ */

import { _fmtDate, _escAttr, showToast } from "../utils.js";
import { getAuthToken, setAuthToken, clearAuthToken, apiAuth, API_BASE } from "../api.js";
import { _skeletonBlock, _setBusy } from "../skeleton.js";
import { setCurrentUser } from "../session.js";
import { navigate } from "../nav.js";
import { refreshBell, _hideBell } from "./alerts.js";

// ─── AUTH (KULLANICI GİRİŞİ) ──────────────────────────────────
// Token yönetimi lib/api.js'den import edildi (getAuthToken, setAuthToken, clearAuthToken).

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

/**
 * Auth gate — REBUILD Faz 3.5. `user` varsa app shell'i göster + landing'i gizle;
 * yoksa tersi. Tek kaynak: refreshAuthState her durumda çağırır.
 */
function _applyAuthGate(user) {
    const welcome = document.getElementById('welcome');
    const landing = document.getElementById('landing');
    const app = document.querySelector('.app');
    if (!landing || !app) return;
    if (user) {
        if (welcome) welcome.style.display = 'none';
        landing.style.display = 'none';
        app.style.display = '';  // flex (CSS default)
    } else {
        // Girişsiz akış: önce hoşgeldin ekranı. Login formu (#landing) yalnız
        // welcome'daki "Giriş Yap" (goToLogin) ile açılır. Logout → welcome'a döner.
        if (welcome) welcome.style.display = 'flex';
        landing.style.display = 'none';
        app.style.display = 'none';
    }
}

/** Welcome → login formu (#landing) geçişi. */
export function goToLogin() {
    const welcome = document.getElementById('welcome');
    const landing = document.getElementById('landing');
    if (welcome) welcome.style.display = 'none';
    if (landing) landing.style.display = 'flex';
    const email = document.getElementById('loginEmail');
    if (email) email.focus();
}

/** Login formundan welcome'a geri dön. */
export function goToWelcome() {
    const welcome = document.getElementById('welcome');
    const landing = document.getElementById('landing');
    if (landing) landing.style.display = 'none';
    if (welcome) welcome.style.display = 'flex';
}

/**
 * Rol-aware görünürlük — `[data-role]` taşıyan elemanları yalnız eşleşen role
 * gösterir (örn. admin "Kullanıcılar"). user null ise hepsi gizli.
 * `.user-badge-role` HARİÇ tutulur: o span data-role'ü SADECE CSS renk kodu için
 * taşır, görünürlük gating'ine girmemeli (badge görünürken her zaman görünmeli).
 * (export: vitest birim testi için.)
 */
export function _applyRoleVisibility(user) {
    document.querySelectorAll('[data-role]:not(.user-badge-role)').forEach(el => {
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
        setCurrentUser(null);
        _renderUserBadge(null);
        _applyRoleVisibility(null);
        _applyAuthGate(null);
        _hideBell();
        return;
    }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (!resp.ok) { clearAuthToken(); refreshAuthState(); return; }
        const me = await resp.json();
        setCurrentUser(me);
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
        setCurrentUser(null);
        _renderUserBadge(null);
        _applyRoleVisibility(null);
        _applyAuthGate(null);
        _hideBell();
    }
}

/**
 * v5-5: Inline field error helper'ları.
 * - _setFieldError(inputId, msg): form-group'a `has-error` ekler + `.field-error` doldurur,
 *   aria-invalid="true" yapar (screen reader)
 * - _clearFieldError(inputId): tüm error state'i temizler
 * - _clearAllErrors(...ids): birden çok alanı bir kerede temizle
 *
 * Toast'a ek olarak alanı işaretler — kullanıcı hatanın hangi alanda olduğunu görür.
 */
function _setFieldError(inputId, msg) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const group = input.closest('.form-group');
    if (!group) return;
    group.classList.add('has-error');
    let errEl = group.querySelector('.field-error');
    if (!errEl) {
        errEl = document.createElement('div');
        errEl.className = 'field-error';
        errEl.setAttribute('role', 'alert');
        group.appendChild(errEl);
    }
    errEl.textContent = msg;
    input.setAttribute('aria-invalid', 'true');
}
function _clearFieldError(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const group = input.closest('.form-group');
    if (!group) return;
    group.classList.remove('has-error');
    input.removeAttribute('aria-invalid');
    const errEl = group.querySelector('.field-error');
    if (errEl) errEl.textContent = '';
}
function _clearAllErrors(...ids) { ids.forEach(_clearFieldError); }

export async function doLogin() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    _clearAllErrors('loginEmail', 'loginPassword');
    let hasError = false;
    if (!email) { _setFieldError('loginEmail', 'E-posta gerekli.'); hasError = true; }
    if (!password) { _setFieldError('loginPassword', 'Şifre gerekli.'); hasError = true; }
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
        await refreshAuthState();   // gate'i açar (app görünür)
        navigate('dashboard');      // gerçek bir sayfaya in
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    }
}

export async function doRegister() {
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;
    _clearAllErrors('regName', 'regEmail', 'regPassword');
    let hasError = false;
    if (!name) { _setFieldError('regName', 'Ad gerekli.'); hasError = true; }
    if (!email) { _setFieldError('regEmail', 'E-posta gerekli.'); hasError = true; }
    if (!password) {
        _setFieldError('regPassword', 'Şifre gerekli.');
        hasError = true;
    } else if (password.length < 8) {
        _setFieldError('regPassword', 'Şifre en az 8 karakter olmalı.');
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
        // Otomatik giriş
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
    const confirm = document.getElementById('pwConfirm').value;
    if (!current || !next || !confirm) {
        showToast('Tüm alanlar gerekli', 'warning');
        return;
    }
    if (next.length < 8) {
        showToast('Yeni şifre en az 8 karakter olmalı', 'warning');
        return;
    }
    if (next !== confirm) {
        showToast('Yeni şifreler eşleşmiyor', 'warning');
        return;
    }
    if (next === current) {
        showToast('Yeni şifre mevcuttan farklı olmalı', 'warning');
        return;
    }
    const token = getAuthToken();
    if (!token) { showToast('Giriş yapman gerekiyor', 'warning'); location.hash = '#auth'; return; }
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
        // Form temizliği
        document.getElementById('pwCurrent').value = '';
        document.getElementById('pwNew').value = '';
        document.getElementById('pwConfirm').value = '';
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    }
}

// ─── ADMIN KULLANICI YÖNETİMİ (REBUILD Faz 3.5) ───────────────
// Tüm çağrılar apiAuth (401→login, 403→yetki toast). Yalnız admin nav görür.

export async function loadUsers() {
    const tbl = document.getElementById('usersTable');
    tbl.innerHTML = _skeletonBlock(5);
    _setBusy('usersTable', true);
    const list = await apiAuth('/api/auth/users?limit=500');
    if (!list) {
        tbl.innerHTML = '<p class="detail-empty">Kullanıcı listesi alınamadı (yetki gerekli).</p>';
        _setBusy('usersTable', false);
        return;
    }
    const roleOpts = (sel) => ['farmer', 'developer', 'overseer', 'admin']
        .map(r => `<option value="${r}"${r === sel ? ' selected' : ''}>${ROLE_LABELS[r]}</option>`).join('');
    let html = '<table class="detail-table"><caption class="sr-only">Kullanıcı listesi</caption><thead><tr>'
        + '<th>Ad</th><th>E-posta</th><th>Rol</th><th>Çiftlik</th><th>Kayıt</th><th>İşlem</th></tr></thead><tbody>';
    for (const u of list) {
        html += `<tr>
            <td>${_escAttr(u.name)}</td>
            <td>${_escAttr(u.email)}</td>
            <td><select class="user-role-select" data-action="changeUserRole" data-id="${u.id}">${roleOpts(u.role)}</select></td>
            <td>${u.owned_farms_count ?? 0}</td>
            <td>${_fmtDate(u.created_at)}</td>
            <td class="user-actions">
                <button class="btn-mini" data-action="resetUserPassword" data-id="${u.id}" data-name="${_escAttr(u.email)}">🔑 Şifre</button>
                <button class="btn-mini btn-danger" data-action="deleteUser" data-id="${u.id}" data-name="${_escAttr(u.email)}">🗑 Sil</button>
            </td>
        </tr>`;
    }
    html += '</tbody></table>';
    tbl.innerHTML = html;
    _setBusy('usersTable', false);
}

export async function createUser() {
    const name = document.getElementById('newUserName').value.trim();
    const email = document.getElementById('newUserEmail').value.trim();
    const password = document.getElementById('newUserPassword').value;
    const role = document.getElementById('newUserRole').value;
    if (!name || !email || !password) { showToast('Ad, e-posta ve şifre gerekli', 'warning'); return; }
    if (password.length < 8) { showToast('Şifre en az 8 karakter olmalı', 'warning'); return; }
    const res = await apiAuth('/api/auth/users', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role }),
    });
    if (res) {
        showToast(`${ROLE_LABELS[role]} oluşturuldu ✅`, 'success');
        document.getElementById('newUserName').value = '';
        document.getElementById('newUserEmail').value = '';
        document.getElementById('newUserPassword').value = '';
        loadUsers();
    }
    // apiAuth 409/400'de null döner + toast; ek mesaj gerekmiyor.
}

export async function changeUserRole(userId, role) {
    const res = await apiAuth(`/api/auth/users/${userId}/role`, {
        method: 'PATCH',
        body: JSON.stringify({ role }),
    });
    if (res) {
        showToast(`Rol güncellendi: ${ROLE_LABELS[role]}`, 'success');
        loadUsers();
    } else {
        // 409 (kendi rolü) vb. — listeyi eski haline çek
        loadUsers();
    }
}

export async function resetUserPassword(userId, email) {
    const np = prompt(`${email} için yeni şifre (min 8 karakter):`);
    if (np === null) return;  // iptal
    if (np.length < 8) { showToast('Şifre en az 8 karakter olmalı', 'warning'); return; }
    const res = await apiAuth(`/api/auth/users/${userId}/password`, {
        method: 'PATCH',
        body: JSON.stringify({ new_password: np }),
    });
    if (res) showToast('Şifre sıfırlandı ✅', 'success');
}

export async function deleteUser(userId, email) {
    if (!confirm(`${email} kullanıcısını silmek istediğine emin misin? Bu geri alınamaz.`)) return;
    const token = getAuthToken();
    if (!token) { location.hash = '#auth'; return; }
    try {
        const resp = await fetch(`${API_BASE}/api/auth/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        if (resp.status === 204) {
            showToast('Kullanıcı silindi', 'success');
            loadUsers();
        } else {
            const err = await resp.json().catch(() => ({}));
            showToast(err.detail || `Silinemedi (${resp.status})`, 'error');
        }
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
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
    showToast('Çıkış yapıldı', 'info');
    await refreshAuthState();    // gate landing'i geri getirir
    toggleLandingForm('login');  // login formuna dön
    if (location.hash) location.hash = '';  // deep route'tan temizle
}
