import { api, apiAuth } from "./api.js";
import { _skeletonRows, _setBusy } from "./skeleton.js";
import { showToast, escAttr as _escAttr } from "./ui_helpers.js";

const PAGE_SIZE = 50;

// ─── IRRIGATION ───────────────────────────────────────────────
// Pagination: sayfa basi 50 kayit, slider ile sayfalari gez.
let irrigationPage = 1;
let irrigationTotal = 0;

export async function loadIrrigation(page = 1) {
    document.getElementById('irrigationTable').innerHTML = _skeletonRows(6, 5);
    _setBusy('irrigationTable', true);
    if (irrigationTotal === 0) {
        const cnt = await api('/api/irrigation/schedules/count');
        irrigationTotal = cnt?.total || 0;
    }
    const totalPages = Math.max(1, Math.ceil(irrigationTotal / PAGE_SIZE));
    irrigationPage = Math.min(Math.max(1, page), totalPages);
    const skip = (irrigationPage - 1) * PAGE_SIZE;

    const schedules = await api(`/api/irrigation/schedules?skip=${skip}&limit=${PAGE_SIZE}`) || [];

    // Nav buton'larini guncelle
    document.getElementById('irrigationPrevBtn').disabled = irrigationPage <= 1;
    document.getElementById('irrigationNextBtn').disabled = irrigationPage >= totalPages;

    // Status bar
    const from = schedules.length ? skip + 1 : 0;
    const to = skip + schedules.length;
    document.getElementById('irrigationPageStatus').innerHTML =
        `Sayfa <strong>${irrigationPage}</strong>/${totalPages} · ` +
        `Kayıt <strong>${from}–${to}</strong>/${irrigationTotal}`;

    document.getElementById('irrigationTable').innerHTML = schedules.map(s => `
        <tr>
            <td>Tarla #${s.field_id}</td><td>${new Date(s.scheduled_date).toLocaleDateString('tr')}</td>
            <td>${s.duration_min || '—'} dk</td><td>${s.water_amount_liters?.toFixed(0) || '—'}</td>
            <td><span class="badge ${s.status}">${s.status}</span></td>
        </tr>
    `).join('');
    _setBusy('irrigationTable', false);
}

let _lastIrrigationRec = null;  // son tahminin önerilen su miktarı (onay için)

/** Kullanıcının tarlalarını <option> HTML'i olarak getir (onay dropdown'ı için). */
async function _myFieldOptions() {
    const farms = await apiAuth('/api/farms/?limit=100');
    if (!farms || farms.length === 0) return '';
    const details = await Promise.all(farms.map(f => apiAuth(`/api/farms/${f.id}`)));
    let opts = '';
    for (const farm of details) {
        if (!farm) continue;
        for (const f of (farm.fields || [])) {
            opts += `<option value="${f.id}">${_escAttr(farm.name)} › ${_escAttr(f.name)}</option>`;
        }
    }
    return opts;
}

export async function predictIrrigation() {
    const body = {
        soil_moisture: +document.getElementById('irr_moisture').value,
        soil_temperature: +document.getElementById('irr_soil_temp').value,
        humidity: +document.getElementById('irr_humidity').value,
        temperature: +document.getElementById('irr_temp').value,
        precipitation: +document.getElementById('irr_precip').value,
    };
    const result = await api('/api/irrigation/predict', { method: 'POST', body: JSON.stringify(body) });
    if (result) {
        _lastIrrigationRec = result.recommended_water_liters;
        const color = result.irrigation_needed ? 'var(--accent-amber)' : 'var(--primary)';
        const fieldOpts = await _myFieldOptions();
        const approveBlock = fieldOpts
            ? `<div class="irr-approve">
                   <label for="irrApproveField">Tarla seç:</label>
                   <select id="irrApproveField">${fieldOpts}</select>
                   <button class="btn-primary" data-action="approveIrrigation">✅ Onayla ve programa ekle</button>
               </div>`
            : `<p style="font-size:.8rem;color:var(--text-dim)">Programa eklemek için önce <a href="#fields">tarla ekle</a>.</p>`;
        document.getElementById('irrigationResult').innerHTML = `
            <div class="result-card">
                <h4>${result.irrigation_needed ? '⚠️ Sulama Gerekli' : '✅ Sulama Gerekmiyor'}</h4>
                <div class="value" style="color:${color}">${result.recommended_water_liters} L</div>
                <p style="margin-top:8px;color:var(--text-muted)">${result.message}</p>
                <p style="margin-top:4px;font-size:.8rem;color:var(--text-dim)">Güven: %${(result.confidence*100).toFixed(0)}</p>
                ${approveBlock}
            </div>`;
        showToast('Sulama tahmini tamamlandı', 'success');
    } else {
        showToast('Tahmin başarısız', 'error');
    }
}

/** Tahmin sonucunu seçili tarla için sulama programına ekle (POST /schedules). */
export async function approveIrrigation() {
    const sel = document.getElementById('irrApproveField');
    if (!sel || !sel.value) { showToast('Lütfen bir tarla seç', 'warning'); return; }
    const body = {
        field_id: parseInt(sel.value, 10),
        scheduled_date: new Date().toISOString(),
        water_amount_liters: _lastIrrigationRec ?? 0,
    };
    const res = await apiAuth('/api/irrigation/schedules', { method: 'POST', body: JSON.stringify(body) });
    if (res) {
        showToast('Sulama programa eklendi ✅ (durum: pending)', 'success');
        irrigationTotal = 0;  // sayacı tazele
        loadIrrigation(1);
    }
}

/** Sulama programı durumunu güncelle (field detail tamamla/iptal butonları). */
export async function updateIrrigationStatus(scheduleId, status) {
    const res = await apiAuth(`/api/irrigation/schedules/${scheduleId}/status`, {
        method: 'PATCH', body: JSON.stringify({ status }),
    });
    if (res) {
        showToast(`Sulama durumu: ${status}`, 'success');
        window.dispatchEvent(new CustomEvent('refreshFieldDetail'));
    }
}

/** Tarla detayından hızlı sulama programı ekle (bugün, su miktarı sorulur). */
export async function addFieldIrrigation(fieldId) {
    const liters = prompt('Su miktarı (litre):', '200');
    if (liters === null) return;
    const amount = parseFloat(liters);
    if (!Number.isFinite(amount) || amount <= 0) { showToast('Geçerli bir su miktarı gir', 'warning'); return; }
    const body = {
        field_id: fieldId,
        scheduled_date: new Date().toISOString(),
        water_amount_liters: amount,
    };
    const res = await apiAuth('/api/irrigation/schedules', { method: 'POST', body: JSON.stringify(body) });
    if (res) { showToast('Sulama programı eklendi ✅', 'success'); window.dispatchEvent(new CustomEvent('refreshFieldDetail')); }
}
