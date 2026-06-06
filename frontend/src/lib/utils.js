/* ============================================================
   SFDAP — Utility Functions
   ============================================================
   Format helpers, toast notifications ve saat göstergesi.
   ============================================================ */

// ─── Format Helpers ───────────────────────────────────────────

export function _fmtDate(iso) {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' }); }
    catch { return iso; }
}

export function _fmtNumber(v, decimals = 1) {
    if (v === null || v === undefined) return '—';
    return Number(v).toLocaleString('tr-TR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function _escAttr(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/<>/g, '&lt;').replace(/>/g, '&gt;');
}

// ─── Toast Notifications ──────────────────────────────────────

export function showToast(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" aria-label="Kapat" title="Kapat">×</button>
    `;
    container.appendChild(toast);

    let timer = null;
    const dismiss = () => {
        clearTimeout(timer);
        toast.classList.add('hide');
        setTimeout(() => toast.remove(), 250);
    };
    toast.querySelector('.toast-close').addEventListener('click', dismiss);
    if (duration > 0) timer = setTimeout(dismiss, duration);
}

// ─── Status & Clock ───────────────────────────────────────────

export function updateStatus(online) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    dot.className = `status-dot ${online ? 'online' : 'offline'}`;
    text.textContent = online ? 'Sistem Aktif' : 'Bağlantı Yok';
}

export function updateClock() {
    document.getElementById('clockDisplay').textContent = new Date().toLocaleTimeString('tr');
}
