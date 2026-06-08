/* ============================================================
   SFDAP — API Service Module
   ============================================================
   Tüm backend iletişimi bu modülden geçer. Auth header bind'i,
   error envelope çözümleme ve token yönetimi tek noktadan yapılır.
   ============================================================ */

const API_BASE = window.location.origin;
const AUTH_TOKEN_KEY = 'sfdap_auth_token';

// ─── Token Yönetimi ───────────────────────────────────────────
export function getAuthToken() { return localStorage.getItem(AUTH_TOKEN_KEY); }
export function setAuthToken(t) { localStorage.setItem(AUTH_TOKEN_KEY, t); }
export function clearAuthToken() { localStorage.removeItem(AUTH_TOKEN_KEY); }

/**
 * Auth header builder — Bearer token varsa Authorization, yoksa X-API-Key.
 */
export function _authHeaders() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return token
        ? { 'Authorization': `Bearer ${token}` }
        : { 'X-API-Key': 'dev-api-key' };
}

/**
 * Backend hata envelope'undan kullanıcıya gösterilecek mesaj üret.
 */
export async function _extractErrorMessage(res) {
    try {
        const body = await res.clone().json();
        if (body && typeof body.message === "string" && body.message.trim()) return body.message;
        if (body && typeof body.detail === "string" && body.detail.trim()) return body.detail;
    } catch {
        // body JSON değil veya parse hatası — generic mesaja düş
    }
    return `HTTP ${res.status}`;
}

/**
 * Genel API çağrısı — auth header otomatik eklenir.
 */
export async function api(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ..._authHeaders(), ...options.headers },
            ...options
        });
        if (!res.ok) {
            const msg = await _extractErrorMessage(res);
            throw new Error(msg);
        }
        return await res.json();
    } catch (e) {
        console.warn(`API Error: ${endpoint}`, e);
        return null;
    }
}

/**
 * Bearer-zorunlu API çağrısı — token yoksa auth sayfasına yönlendirir.
 * @param {Function} showToast - Toast gösterme fonksiyonu (circular dep önlemek için parametre)
 * @param {Function} renderUserBadge - Badge render fonksiyonu
 */
let _showToast = null;
let _renderUserBadge = null;
let _setCurrentUser = null;

export function initApiCallbacks({ showToast, renderUserBadge, setCurrentUser }) {
    _showToast = showToast;
    _renderUserBadge = renderUserBadge;
    _setCurrentUser = setCurrentUser;
}

export async function apiAuth(endpoint, options = {}) {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
        if (location.hash !== '#auth') location.hash = '#auth';
        return null;
    }
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`, ...options.headers },
            ...options
        });
        if (res.status === 401) {
            localStorage.removeItem(AUTH_TOKEN_KEY);
            _setCurrentUser?.(null);
            _renderUserBadge?.(null);
            _showToast?.('Oturum süresi doldu, tekrar giriş yap', 'warning');
            location.hash = '#auth';
            return null;
        }
        if (res.status === 403) {
            const msg = await _extractErrorMessage(res);
            _showToast?.(msg.startsWith('HTTP ') ? 'Bu işlem için yetkin yok' : msg, 'warning');
            return null;
        }
        if (!res.ok) {
            const msg = await _extractErrorMessage(res);
            _showToast?.(msg, 'error');
            throw new Error(msg);
        }
        return await res.json();
    } catch (e) {
        console.warn(`API Auth Error: ${endpoint}`, e);
        if (e instanceof TypeError) _showToast?.('Sunucuya ulaşılamadı', 'error');
        return null;
    }
}

export { API_BASE, AUTH_TOKEN_KEY };
