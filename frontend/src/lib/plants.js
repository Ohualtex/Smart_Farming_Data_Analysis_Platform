import { api } from "./api.js";
import { showToast } from "./ui_helpers.js";

// ─── PLANTS (BİTKİ SAĞLIĞI) ───────────────────────────────────
export async function loadPlants() {
    const tbl = document.getElementById('plantsHistoryTable');
    // Generic block skeleton (target is a div, not a tbody).
    tbl.innerHTML = _skeletonBlock(4);
    _setBusy('plantsHistoryTable', true);
    const list = await api('/api/plants/health-images?limit=20');
    if (!list || list.length === 0) {
        tbl.innerHTML = '<p style="text-align:center;color:var(--text-muted);padding:24px;">Henüz analiz edilmiş görsel yok.</p>';
        _setBusy('plantsHistoryTable', false);
        return;
    }
    let html = '<table style="width:100%;border-collapse:collapse;"><caption class="sr-only">Bitki sağlığı analiz geçmişi</caption><thead><tr>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Tarih</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Tarla</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Teşhis</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Güven</th>'
        + '<th scope="col" style="text-align:left;padding:8px;border-bottom:1px solid var(--border);">Şiddet</th>'
        + '</tr></thead><tbody>';
    for (const r of list) {
        const sev = r.severity || '—';
        const sevColor = sev === 'high' ? '#ef4444' : sev === 'medium' ? '#f59e0b' : sev === 'low' ? '#eab308' : '#22c55e';
        const conf = r.confidence_score ? (r.confidence_score * 100).toFixed(0) + '%' : '—';
        const date = r.captured_at ? new Date(r.captured_at).toLocaleDateString('tr-TR') : '—';
        html += `<tr>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${date}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">#${r.field_id}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${r.diagnosis || '—'}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${conf}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);"><span style="color:${sevColor};font-weight:600;">${sev}</span></td>
        </tr>`;
    }
    html += '</tbody></table>';
    tbl.innerHTML = html;
    _setBusy('plantsHistoryTable', false);
}

export async function analyzePlantImage() {
    const fieldId = document.getElementById('plantsFieldId').value;
    const fileInput = document.getElementById('plantsFile');
    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Lütfen bir görsel seç', 'warning');
        return;
    }
    const file = fileInput.files[0];
    if (file.size > 5 * 1024 * 1024) {
        showToast('Dosya 5 MB\'dan büyük', 'error');
        return;
    }
    const btn = document.getElementById('plantsAnalyzeBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Analiz ediliyor...';
    const fd = new FormData();
    fd.append('field_id', fieldId);
    fd.append('image', file);
    try {
        const resp = await fetch(`${API_BASE}/api/plants/health-images/analyze`, {
            method: 'POST',
            headers: { ..._authHeaders() },  // Bearer (RBAC) — yoksa X-API-Key fallback
            body: fd,
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            showToast(err.detail || `Hata ${resp.status}`, 'error');
            return;
        }
        const data = await resp.json();
        renderPlantResult(data);
        showToast('Analiz tamamlandı', 'success');
        loadPlants();
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔬 Hastalığı Tespit Et';
    }
}

function renderPlantResult(data) {
    const sev = data.severity || 'none';
    const sevColor = sev === 'high' ? '#ef4444' : sev === 'medium' ? '#f59e0b' : sev === 'low' ? '#eab308' : '#22c55e';
    const conf = (data.confidence_score * 100).toFixed(1);
    let html = `<div class="form-box" style="border-left:4px solid ${sevColor};">
        <h3 style="margin-top:0;">🧪 Sonuç: ${data.diagnosis}</h3>
        <p><strong>Güven:</strong> %${conf}</p>
        <p><strong>Şiddet:</strong> <span style="color:${sevColor};font-weight:600;">${sev}</span></p>
        <p><strong>Model:</strong> ${data.model_version}</p>
        <details style="margin-top:12px;"><summary style="cursor:pointer;">Tüm sınıf skorları</summary>
        <ul style="margin-top:8px;">`;
    for (const [cls, score] of Object.entries(data.all_scores || {})) {
        html += `<li>${cls}: ${(score * 100).toFixed(1)}%</li>`;
    }
    html += '</ul></details></div>';
    const box = document.getElementById('plantsResultBox');
    box.innerHTML = html;
    box.style.display = 'block';
}

// File input preview — hem plants sayfası hem tarla detayı leaf upload'ı.
document.addEventListener('change', (e) => {
    if (!e.target) return;
    if (e.target.id === 'plantsFile') {
        const file = e.target.files && e.target.files[0];
        const wrap = document.getElementById('plantsPreviewWrap');
        const img = document.getElementById('plantsPreview');
        if (!file) { wrap.style.display = 'none'; return; }
        img.src = URL.createObjectURL(file);
        wrap.style.display = 'block';
    } else if (e.target.id === 'fieldLeafFile') {
        const file = e.target.files && e.target.files[0];
        const wrap = document.getElementById('fieldLeafPreviewWrap');
        const img = document.getElementById('fieldLeafPreview');
        if (!wrap || !img) return;
        if (!file) { wrap.style.display = 'none'; return; }
        img.src = URL.createObjectURL(file);
        wrap.style.display = 'block';
    }
});
