import { api, apiAuth } from "./api.js";
import { _skeletonRows, _setBusy } from "./skeleton.js";
import { showToast, escAttr as _escAttr } from "./ui_helpers.js";

const PAGE_SIZE = 50;

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
            <td style="padding:8px;border-bottom:1px solid var(--border);"><span style="color:${sevColor};font-weight:600;">${a.severity}</span></td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${a.alert_type}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${a.message}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${status}</td>
        </tr>`;
    }
    html += '</tbody></table>';
    tbl.innerHTML = html;
    _setBusy('alertsTable', false);
}

export async function resolveAlert(id) {
    try {
        const resp = await fetch(`${API_BASE}/api/alerts/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'X-API-Key': 'dev-api-key' },
            body: JSON.stringify({ is_resolved: true }),
        });
        if (resp.ok) {
            showToast('Uyarı çözüldü olarak işaretlendi', 'success');
            loadAlerts();
        } else {
            showToast(`Hata ${resp.status}`, 'error');
        }
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    }
}
