/* ============================================================
   SFDAP — Alerts Page + Notification Bell Module
   ============================================================
   Uyarılar sayfası (liste + çöz) ve header bildirim çanı
   (refreshBell/toggleBell/_hideBell/resolveFromBell/runAlertCheck).
   _hideBell/refreshBell account.js refreshAuthState'ten çağırılır.
   ============================================================ */

import { _escAttr, showToast } from "../utils.js";
import { api, apiAuth, API_BASE } from "../api.js";
import { _skeletonCards, _skeletonBlock, _setBusy } from "../skeleton.js";
import { severityLabel, alertTypeLabel } from "../labels.js";

// ─── ALERTS ───────────────────────────────────────────────────
export async function loadAlerts() {
    const tbl = document.getElementById('alertsTable');
    const cards = document.getElementById('alertsSummaryCards');
    // Skeleton + aria-busy before the fetch.
    cards.innerHTML = _skeletonCards(3);
    tbl.innerHTML = _skeletonBlock(5);
    _setBusy('alertsSummaryCards', true);
    _setBusy('alertsTable', true);

    const sev = document.getElementById('alertSeverity')?.value || '';
    const resolved = document.getElementById('alertResolved')?.value || '';
    let qs = 'limit=100';
    if (sev) qs += `&severity=${encodeURIComponent(sev)}`;
    if (resolved) qs += `&is_resolved=${resolved}`;
    const list = await api(`/api/alerts/?${qs}`);

    // Özet kartları
    const total = list ? list.length : 0;
    const critical = list ? list.filter(a => a.severity === 'critical').length : 0;
    const open = list ? list.filter(a => !a.is_resolved).length : 0;
    cards.innerHTML = `
        <div class="card"><div class="card-icon" aria-hidden="true">📋</div><div class="card-value">${total}</div><div class="card-label">Toplam</div></div>
        <div class="card"><div class="card-icon" aria-hidden="true">⚠️</div><div class="card-value">${open}</div><div class="card-label">Açık</div></div>
        <div class="card"><div class="card-icon" aria-hidden="true">🚨</div><div class="card-value">${critical}</div><div class="card-label">Kritik</div></div>`;
    _setBusy('alertsSummaryCards', false);

    if (!list || list.length === 0) {
        tbl.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:24px;">Bu filtre için uyarı yok.</p>';
        _setBusy('alertsTable', false);
        return;
    }
    let html = '<table style="width:100%;border-collapse:collapse;"><caption class="sr-only">Sistem uyarıları listesi</caption><thead><tr>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Tarih</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Öncelik</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Tip</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Mesaj</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Durum</th>'
        + '</tr></thead><tbody>';
    for (const a of list) {
        const sevColor = a.severity === 'critical' ? '#ef4444' : a.severity === 'medium' ? '#f59e0b' : '#eab308';
        const date = a.created_at ? new Date(a.created_at).toLocaleString('tr-TR') : '—';
        const status = a.is_resolved
            ? '<span style="color:#22c55e;">✓ Çözüldü</span>'
            : `<button class="btn-secondary" style="padding:4px 10px;" data-action="resolveAlert" data-id="${a.id}" aria-label="Uyarıyı çözüldü olarak işaretle">Çöz</button>`;
        html += `<tr>
            <td style="padding:8px;border-bottom:1px solid var(--border);font-size:.85rem;">${date}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);"><span style="color:${sevColor};font-weight:600;">${severityLabel(a.severity)}</span></td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${alertTypeLabel(a.alert_type)}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${_escAttr(a.message)}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${status}</td>
        </tr>`;
    }
    html += '</tbody></table>';
    tbl.innerHTML = html;
    _setBusy('alertsTable', false);
}

export async function resolveAlert(id) {
    const res = await apiAuth(`/api/alerts/${id}`, { method: 'PATCH', body: JSON.stringify({ is_resolved: true }) });
    if (res) {
        showToast('Uyarı çözüldü olarak işaretlendi', 'success');
        loadAlerts();
    }
}

// ─── BİLDİRİM ÇANI (REBUILD Faz 5) ────────────────────────────
export function _hideBell() {
    const wrap = document.getElementById('notifWrap');
    if (wrap) wrap.style.display = 'none';
    const dd = document.getElementById('notifDropdown');
    if (dd) dd.style.display = 'none';
}

/** Açık uyarıları çek, çan sayısını + dropdown listesini güncelle. */
export async function refreshBell() {
    const wrap = document.getElementById('notifWrap');
    if (!wrap) return;
    wrap.style.display = 'inline-flex';
    const alerts = await apiAuth('/api/alerts/?is_resolved=false&limit=20');
    const countEl = document.getElementById('notifCount');
    const listEl = document.getElementById('notifList');
    const open = alerts || [];
    if (countEl) {
        countEl.textContent = open.length > 9 ? '9+' : String(open.length);
        countEl.style.display = open.length > 0 ? 'inline-flex' : 'none';
    }
    document.getElementById('notifBell')?.classList.toggle('has-unread', open.length > 0);
    if (listEl) {
        listEl.innerHTML = open.length === 0
            ? '<div class="notif-empty">Açık uyarı yok ✅</div>'
            : open.slice(0, 10).map(a => `
                <div class="notif-item severity-${_escAttr(a.severity)}">
                    <div class="notif-item-msg">${_escAttr(a.message)}</div>
                    <div class="notif-item-foot">
                        <span class="notif-item-sev">${_escAttr(severityLabel(a.severity))}</span>
                        <button class="btn-mini" data-action="resolveFromBell" data-id="${a.id}">Çöz</button>
                    </div>
                </div>`).join('');
    }
}

export function toggleBell() {
    const dd = document.getElementById('notifDropdown');
    const bell = document.getElementById('notifBell');
    if (!dd) return;
    const open = dd.style.display !== 'none' && dd.style.display !== '';
    dd.style.display = open ? 'none' : 'block';
    if (bell) bell.setAttribute('aria-expanded', open ? 'false' : 'true');
    if (!open) refreshBell();  // açarken tazele
}

/** "Kontrol et" — tarlaları tara, uyarı üret, çanı tazele. */
export async function runAlertCheck() {
    const res = await apiAuth('/api/alerts/check', { method: 'POST' });
    if (res) {
        showToast(res.created > 0 ? `${res.created} yeni uyarı üretildi` : 'Yeni uyarı yok ✅', res.created > 0 ? 'warning' : 'success');
        refreshBell();
    }
}

/** Çan dropdown'ından uyarı çöz. */
export async function resolveFromBell(alertId) {
    const res = await apiAuth(`/api/alerts/${alertId}`, { method: 'PATCH', body: JSON.stringify({ is_resolved: true }) });
    if (res) { showToast('Uyarı çözüldü', 'success'); refreshBell(); }
}

// Dropdown dışına tıklayınca kapat
document.addEventListener('click', (e) => {
    const wrap = document.getElementById('notifWrap');
    const dd = document.getElementById('notifDropdown');
    if (wrap && dd && !wrap.contains(e.target) && dd.style.display === 'block') {
        dd.style.display = 'none';
        document.getElementById('notifBell')?.setAttribute('aria-expanded', 'false');
    }
});
