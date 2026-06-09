/* ============================================================
   SFDAP — Monitoring Pages Module
   ============================================================
   Sensörler, Hava Durumu, Sulama, Gübreleme, Raporlar (Analytics),
   Harita ve Bitki Sağlığı sayfaları. Sayfa-yerel pagination/öneri
   state'i bu modülde tutulur.
   ============================================================ */

import { _escAttr, showToast } from "../utils.js";
import { api, apiAuth, getAuthToken, API_BASE, _authHeaders } from "../api.js";
import { _skeletonCards, _skeletonRows, _skeletonBlock, _setBusy } from "../skeleton.js";
import { irrigationStatusLabel, diagnosisLabel, severityLabel, sensorTypeLabel, sensorStatusLabel } from "../labels.js";
import { charts, renderSensorTypeChart, renderFarmTempChart, renderIrrigationStatusChart,
         renderNpkRadarChart, renderDailyTrendChart, renderSensorStatsChart,
         chartTick, chartLegend, chartGrid } from "../charts.js";
import { loadMap as _loadMapImpl } from "../map.js";
import { renderPlantResult } from "../render.js";
import { getCurrentFieldId, loadFieldDetail } from "./fields.js";

// ─── SENSORS ──────────────────────────────────────────────────
// Pagination: sayfa basi 50 kayit, slider ile sayfalari gez.
const PAGE_SIZE = 50;
let sensorsPage = 1;
let sensorsTotal = 0;

/** actionMap (sensorsPrev/Next) mevcut sayfayı okumak için kullanır. */
export function getSensorsPage() { return sensorsPage; }

export async function loadSensors(page = 1) {
    // Table skeleton — 6 rows × 4 columns before the fetch returns.
    document.getElementById('sensorsTable').innerHTML = _skeletonRows(6, 4);
    _setBusy('sensorsTable', true);
    // Toplam sayıyı HER yüklemede tazele: field-detail'den sensör eklenip/silinin
    // (monitoring dışı) cache stale kalıyordu (audit ORTA #24). COUNT ucuz query.
    // Audit fix (#10): Bearer-zorunlu endpoint → apiAuth (api() X-API-Key fallback'i tutarsız).
    const cnt = await apiAuth('/api/sensors/count');
    sensorsTotal = cnt?.total || 0;
    const totalPages = Math.max(1, Math.ceil(sensorsTotal / PAGE_SIZE));
    sensorsPage = Math.min(Math.max(1, page), totalPages);
    const skip = (sensorsPage - 1) * PAGE_SIZE;

    // Audit fix (#10): Bearer-zorunlu endpoint → apiAuth.
    const sensors = await apiAuth(`/api/sensors/?skip=${skip}&limit=${PAGE_SIZE}`) || [];

    // Nav buton'larini guncelle
    document.getElementById('sensorsPrevBtn').disabled = sensorsPage <= 1;
    document.getElementById('sensorsNextBtn').disabled = sensorsPage >= totalPages;

    // Status bar
    const from = sensors.length ? skip + 1 : 0;
    const to = skip + sensors.length;
    document.getElementById('sensorsPageStatus').innerHTML =
        `Sayfa <strong>${sensorsPage}</strong>/${totalPages} · ` +
        `Kayıt <strong>${from}–${to}</strong>/${sensorsTotal}`;

    // Tabloyu render et — a11y: satira role=button + keyboard handler
    // EN / TR: satir click + Enter/Space ile detay yuklenir; tabindex=0 ile
    // keyboard navigation acilir.
    // XSS koruması: sensor_type/status kullanıcı-kaynaklı (SensorCreate.sensor_type
    // serbest str) → escape şart (audit YÜKSEK stored-XSS). serial_number zaten escape'liydi.
    // Audit fix (#27): ham snake_case/İngilizce yerine Türkçe etiket; bilinmeyen
    // değerde fallback ham değeri döndürdüğü için _escAttr sarması korunur.
    document.getElementById('sensorsTable').innerHTML = sensors.map(s => `
        <tr tabindex="0" role="button" aria-label="Sensör ${s.id} (${_escAttr(sensorTypeLabel(s.sensor_type))}) detayını aç"
            style="cursor:pointer" data-action="loadSensorDetail" data-id="${s.id}">
            <td>${s.id}</td><td>${_escAttr(sensorTypeLabel(s.sensor_type))}</td><td>${_escAttr(s.serial_number)}</td>
            <td><span class="badge active">${_escAttr(sensorStatusLabel(s.status))}</span></td>
        </tr>
    `).join('');
    _setBusy('sensorsTable', false);
}

export async function loadSensorDetail(sensorId) {
    // Audit fix (#10): Bearer-zorunlu endpoint → apiAuth.
    const readings = await apiAuth(`/api/sensors/${sensorId}/readings?limit=30`) || [];
    const sorted = [...readings].reverse();
    if (charts.sensorDetail) charts.sensorDetail.destroy();
    charts.sensorDetail = new Chart(document.getElementById('sensorDetailChart'), {
        type: 'line', data: { labels: sorted.map(r => new Date(r.reading_timestamp).toLocaleDateString('tr')),
            datasets: [{ label: 'Nem %', data: sorted.map(r => r.moisture_percent), borderColor: '#10b981',
                backgroundColor: 'rgba(16,185,129,.1)', fill: true, tension: .4 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: chartLegend() } } },
            scales: { x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } }, y: { ticks: { color: chartTick() }, grid: { color: chartGrid() } } } }
    });
    document.getElementById('sensorInfoBox').innerHTML = `<h3>ℹ️ Sensör #${sensorId}</h3>
        <p style="margin:12px 0;color:var(--text-muted)">Toplam ${readings.length} okuma</p>
        ${readings.length ? `<p>Son okuma: <strong>%${readings[0].moisture_percent}</strong></p>
        <p>Son sıcaklık: <strong>${readings[0].soil_temperature_c || '—'}°C</strong></p>` : '<p>Veri yok</p>'}`;
}

// ─── WEATHER ──────────────────────────────────────────────────
export async function loadWeather() {
    document.getElementById('weatherCards').innerHTML = _skeletonCards(4);
    _setBusy('weatherCards', true);
    const data = await api('/api/weather/?limit=30') || [];
    const sorted = [...data].reverse();
    // Cards
    if (data.length) {
        const temps = data.map(d => d.temperature_c).filter(t => t != null);
        document.getElementById('weatherCards').innerHTML = `
            <div class="card"><div class="card-icon" aria-hidden="true">🌡️</div><div class="card-value">${data[0].temperature_c?.toFixed(1) || '—'}°C</div><div class="card-label">Güncel Sıcaklık</div></div>
            <div class="card"><div class="card-icon" aria-hidden="true">💧</div><div class="card-value">%${data[0].humidity_percent?.toFixed(1) || '—'}</div><div class="card-label">Güncel Nem</div></div>
            <div class="card"><div class="card-icon" aria-hidden="true">📊</div><div class="card-value">${temps.length ? Math.min(...temps).toFixed(1) + '—' + Math.max(...temps).toFixed(1) : '—'}°C</div><div class="card-label">Sıcaklık Aralığı</div></div>
            <div class="card"><div class="card-icon" aria-hidden="true">🌧️</div><div class="card-value">${data.reduce((a,d) => a + (d.precipitation_mm||0), 0).toFixed(1)}mm</div><div class="card-label">Toplam Yağış</div></div>
        `;
    } else {
        // Audit fix (#23): veri boş/çevrimdışı ise skeleton kartlar sonsuza
        // dek dönmesin — "Veri yok" durumu göster.
        document.getElementById('weatherCards').innerHTML =
            '<p class="empty-state" style="grid-column: 1 / -1;">🌤️ Hava durumu verisi yok veya sunucuya ulaşılamadı.</p>';
    }
    _setBusy('weatherCards', false);
    // Temperature chart
    const labels = sorted.map(d => new Date(d.recorded_at).toLocaleDateString('tr'));
    if (charts.weatherTemp) charts.weatherTemp.destroy();
    charts.weatherTemp = new Chart(document.getElementById('weatherTempChart'), {
        type: 'line', data: { labels, datasets: [{ label: 'Sıcaklık °C', data: sorted.map(d => d.temperature_c),
            borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.1)', fill: true, tension: .4, pointRadius: 2 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: chartLegend() } } },
            scales: { x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } }, y: { ticks: { color: chartTick() }, grid: { color: chartGrid() } } } }
    });
    // Wind chart
    if (charts.weatherWind) charts.weatherWind.destroy();
    charts.weatherWind = new Chart(document.getElementById('weatherWindChart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Rüzgar km/h', data: sorted.map(d => d.wind_speed_kmh || 0),
            backgroundColor: 'rgba(139,92,246,.4)', borderColor: '#8b5cf6', borderWidth: 1 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: chartLegend() } } },
            scales: { x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } }, y: { ticks: { color: chartTick() }, grid: { color: chartGrid() } } } }
    });
}

// ─── IRRIGATION ───────────────────────────────────────────────
// Pagination: sayfa basi 50 kayit, slider ile sayfalari gez.
let irrigationPage = 1;
let irrigationTotal = 0;

/** actionMap (irrigationPrev/Next) mevcut sayfayı okumak için kullanır. */
export function getIrrigationPage() { return irrigationPage; }

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
            <td><span class="badge ${s.status}">${irrigationStatusLabel(s.status)}</span></td>
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
    // Audit fix (#32): boş input'lar unary + ile 0'a dönüşüp model uydurma sıfırlarla
    // tahmin yapıyordu → her alanı doğrula, boş/NaN varsa toast ile reddet.
    const fields = {
        soil_moisture: 'irr_moisture', soil_temperature: 'irr_soil_temp',
        humidity: 'irr_humidity', temperature: 'irr_temp', precipitation: 'irr_precip',
    };
    const body = {};
    for (const [key, id] of Object.entries(fields)) {
        const raw = document.getElementById(id).value.trim();
        const num = Number(raw);
        if (raw === '' || !Number.isFinite(num)) {
            showToast('Tüm alanları geçerli sayılarla doldur', 'warning');
            return;
        }
        body[key] = num;
    }
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
    if (_lastIrrigationRec == null) { showToast('Önce sulama önerisi hesapla', 'warning'); return; }
    const body = {
        field_id: parseInt(sel.value, 10),
        scheduled_date: new Date().toISOString(),
        water_amount_liters: _lastIrrigationRec,
    };
    const res = await apiAuth('/api/irrigation/schedules', { method: 'POST', body: JSON.stringify(body) });
    if (res) {
        showToast(`Sulama programa eklendi ✅ (durum: ${irrigationStatusLabel('pending')})`, 'success');
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
        showToast(`Sulama durumu: ${irrigationStatusLabel(status)}`, 'success');
        const currentFieldId = getCurrentFieldId();
        if (currentFieldId) loadFieldDetail(currentFieldId);
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
    if (res) { showToast('Sulama programı eklendi ✅', 'success'); loadFieldDetail(fieldId); }
}

// ─── FERTILIZER ───────────────────────────────────────────────
export async function recommendFertilizer() {
    const body = {
        crop_type: document.getElementById('fert_crop').value,
        soil_nitrogen: +document.getElementById('fert_n').value,
        soil_phosphorus: +document.getElementById('fert_p').value,
        soil_potassium: +document.getElementById('fert_k').value,
        area_hectares: +document.getElementById('fert_area').value,
    };
    const r = await api('/api/fertilizer/recommend', { method: 'POST', body: JSON.stringify(body) });
    if (r) {
        document.getElementById('fertilizerResult').innerHTML = `
            <div class="result-card">
                <h4>🌱 ${r.crop_name_tr} — Gübreleme Önerisi</h4>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:16px 0;">
                    <div><div style="font-size:.8rem;color:var(--text-muted)">Azot (N)</div><div style="font-size:1.3rem;font-weight:700;color:#10b981">${r.nitrogen_needed_kg ?? '—'} kg</div></div>
                    <div><div style="font-size:.8rem;color:var(--text-muted)">Fosfor (P)</div><div style="font-size:1.3rem;font-weight:700;color:#3b82f6">${r.phosphorus_needed_kg ?? '—'} kg</div></div>
                    <div><div style="font-size:.8rem;color:var(--text-muted)">Potasyum (K)</div><div style="font-size:1.3rem;font-weight:700;color:#f59e0b">${r.potassium_needed_kg ?? '—'} kg</div></div>
                </div>
                <p style="color:var(--text-muted);font-size:.85rem;">${r.recommendation}</p>
            </div>`;
        showToast('Gübreleme önerisi hazır', 'success');
    }
}

export async function fertilizerSchedule() {
    const body = {
        crop_type: document.getElementById('fert_crop').value,
        planting_date: document.getElementById('fert_date').value,
        area_hectares: +document.getElementById('fert_area').value,
        soil_nitrogen: +document.getElementById('fert_n').value,
        soil_phosphorus: +document.getElementById('fert_p').value,
        soil_potassium: +document.getElementById('fert_k').value,
    };
    const schedule = await api('/api/fertilizer/schedules', { method: 'POST', body: JSON.stringify(body) });
    if (schedule && schedule.length) {
        document.getElementById('scheduleResult').innerHTML = `
            <div class="table-box" style="margin-top:20px;">
                <table><caption class="sr-only">Gübreleme takvimi (fazlara göre)</caption>
                <thead><tr><th scope="col">Faz</th><th scope="col">Tarih</th><th scope="col">Gübre</th><th scope="col">kg/ha</th><th scope="col">Not</th></tr></thead>
                <tbody>${schedule.map(s => `<tr><td>${s.phase}</td><td>${s.target_date}</td><td>${s.fertilizer_type}</td><td>${s.amount_kg_per_hectare}</td><td style="color:var(--text-muted);font-size:.8rem;">${s.notes}</td></tr>`).join('')}</tbody></table>
            </div>`;
        showToast('Gübreleme takvimi oluşturuldu', 'success');
    } else {
        document.getElementById('scheduleResult').innerHTML = '<p class="empty-state">Gübreleme takvimi oluşturulamadı.</p>';
        showToast('Gübreleme takvimi alınamadı', 'error');
    }
}

// ─── ANALYTICS ─────────────────────────────────────────────────

export async function loadAnalytics() {
    document.getElementById('analyticsCards').innerHTML = _skeletonCards(6);
    _setBusy('analyticsCards', true);
    const data = await api('/api/analytics/summary?days=30');
    if (!data) {
        _setBusy('analyticsCards', false);
        showToast('Analitik verisi yüklenemedi', 'error');
        return;
    }

    // Özet Kartları
    const c = data.counts;
    document.getElementById('analyticsCards').innerHTML = `
        <div class="card"><div class="card-icon" aria-hidden="true">🏡</div><div class="card-value">${c.farms}</div><div class="card-label">Çiftlik</div></div>
        <div class="card"><div class="card-icon" aria-hidden="true">🌾</div><div class="card-value">${c.fields}</div><div class="card-label">Tarla</div></div>
        <div class="card"><div class="card-icon" aria-hidden="true">📡</div><div class="card-value">${c.sensors}</div><div class="card-label">Sensör</div></div>
        <div class="card"><div class="card-icon" aria-hidden="true">📊</div><div class="card-value">${c.readings}</div><div class="card-label">Sensör Okuması</div></div>
        <div class="card"><div class="card-icon" aria-hidden="true">🌤️</div><div class="card-value">${c.weather_records}</div><div class="card-label">Hava Durumu Kaydı</div></div>
        <div class="card"><div class="card-icon" aria-hidden="true">💧</div><div class="card-value">${c.irrigation_schedules}</div><div class="card-label">Sulama Programı</div></div>
    `;
    _setBusy('analyticsCards', false);

    renderSensorTypeChart(data.sensor_type_distribution);
    renderFarmTempChart(data.farm_weather_comparison);
    renderIrrigationStatusChart(data.irrigation_status_distribution);
    renderNpkRadarChart(data.npk_profiles);
    renderDailyTrendChart(data.daily_trends);
    renderSensorStatsChart(data.sensor_reading_stats);
}

// ─── MAP (TÜRKİYE HARİTASI) ───────────────────────────────────
// Asıl logic `frontend/src/lib/map.js`'te (B-batch refactor).
// Burada wrapper: navigate() bunu çağırır, lib `api` parametresini alır.
export async function loadMap() {
    return _loadMapImpl({ api });
}

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
        // Audit fix (#18): 0.0 falsy olduğu için '—' görünüyordu → null/undefined kontrolü ile 0% göster.
        const conf = r.confidence_score != null ? (r.confidence_score * 100).toFixed(0) + '%' : '—';
        const date = r.captured_at ? new Date(r.captured_at).toLocaleDateString('tr-TR') : '—';
        html += `<tr>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${date}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">#${r.field_id}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${diagnosisLabel(r.diagnosis)}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);">${conf}</td>
            <td style="padding:8px;border-bottom:1px solid var(--border);"><span style="color:${sevColor};font-weight:600;">${severityLabel(sev)}</span></td>
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
    if (btn.disabled) return;  // çift-submit guard
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
