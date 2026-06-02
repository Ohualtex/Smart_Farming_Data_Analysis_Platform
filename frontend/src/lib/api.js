import { extractErrorMessage } from "./ui_helpers.js";

export const API_BASE = window.location.origin;
export const AUTH_TOKEN_KEY = 'sfdap_auth_token';

/**
 * Auth header builder — Bearer token varsa Authorization, yoksa X-API-Key.
 */
export function getAuthHeaders() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return token
        ? { 'Authorization': `Bearer ${token}` }
        : { 'X-API-Key': 'dev-api-key' };
}

export function getAuthToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
}

export async function api(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ...getAuthHeaders(), ...options.headers },
            ...options
        });
        if (!res.ok) {
            const msg = await extractErrorMessage(res);
            throw new Error(msg);
        }
        return await res.json();
    } catch (e) {
        console.warn(`API Error: ${endpoint}`, e);
        return null;
    }
}

export async function apiAuth(endpoint, options = {}) {
    const token = getAuthToken();
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
            clearAuthToken();
            // We use a custom event instead of hard-coupling to main.js for showing toasts
            window.dispatchEvent(new CustomEvent('auth-expired'));
            location.hash = '#auth';
            return null;
        }
        if (res.status === 403) {
            const msg = await extractErrorMessage(res);
            window.dispatchEvent(new CustomEvent('auth-forbidden', { detail: msg }));
            return null;
        }
        if (!res.ok) {
            const msg = await extractErrorMessage(res);
            window.dispatchEvent(new CustomEvent('api-error', { detail: msg }));
            throw new Error(msg);
        }
        return await res.json();
    } catch (e) {
        console.warn(`API Auth Error: ${endpoint}`, e);
        return null;
    }
}
