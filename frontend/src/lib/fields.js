import { API_BASE, apiAuth, getAuthToken } from "./api.js";
import { _skeletonBlock, _setBusy } from "./skeleton.js";
import { fmtDate as _fmtDate, fmtNumber as _fmtNumber, escAttr as _escAttr, STATUS_EMOJI as _STATUS_EMOJI, STATUS_LABEL as _STATUS_LABEL, showToast, pageTitles } from "./ui_helpers.js";

let fieldReadingsChart = null;

// ─── TARLALARIM (FIELD LIST) ──────────────────────────────────
// REBUILD Faz 3 / Adım 6: çiftlik bazlı tarla listesi.
// /api/farms/ → her farm için /api/farms/{id} (nested fields).
// Tarlalarım sayfasında çiftlik dropdown'ı için son çekilen çiftlik listesi
let _myFarms = [];

export async function loadFields() {
    const container = document.getElementById('fieldsListContainer');
    container.innerHTML = _skeletonBlock(3);
    _setBusy('fieldsListContainer', true);

    const token = getAuthToken();
    if (!token) {
        container.innerHTML = '<div class="empty-state"><p>🔐 Tarlalarını görmek için <a href="#auth">giriş yap</a>.</p></div>';
        _setBusy('fieldsListContainer', false);
        return;
    }

    const farms = await apiAuth('/api/farms/?limit=100');
    if (farms === null) {
        container.innerHTML = '<div class="empty-state"><p>⚠️ Çiftlikler alınamadı.</p></div>';
        _setBusy('fieldsListContainer', false);
        return;
    }
    _myFarms = farms;

    // ─── Eylem çubuğu: çiftlik/tarla ekle (toggle formlar) ───
    const farmOpts = farms.map(f => `<option value="${f.id}">${_escAttr(f.name)}</option>`).join('');
    let html = `
        <div class="crud-actionbar">
            <button class="btn-primary" data-action="toggleForm" data-arg="newFarmForm">➕ Çiftlik Ekle</button>
            ${farms.length ? `<button class="btn-secondary" data-action="toggleForm" data-arg="newFieldForm">➕ Tarla Ekle</button>` : ''}
        </div>
        <div class="form-box crud-form" id="newFarmForm" style="display:none;">
            <h4 style="margin-top:0;">➕ Yeni Çiftlik</h4>
            <div class="form-row">
                <div class="form-group"><label>Ad *</label><input type="text" id="nfName" placeholder="Çiftlik adı" /></div>
                <div class="form-group"><label>İl</label><input type="text" id="nfCity" placeholder="Konya" /></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Bölge</label><input type="text" id="nfRegion" placeholder="İç Anadolu" /></div>
                <div class="form-group"><label>Alan (ha)</label><input type="number" id="nfArea" step="0.1" placeholder="8.0" /></div>
            </div>
            <button class="btn-primary" data-action="submitNewFarm">Kaydet</button>
        </div>
        <div class="form-box crud-form" id="newFieldForm" style="display:none;">
            <h4 style="margin-top:0;">➕ Yeni Tarla</h4>
            <div class="form-row">
                <div class="form-group"><label>Çiftlik *</label><select id="ndFarm">${farmOpts}</select></div>
                <div class="form-group"><label>Ad *</label><input type="text" id="ndName" placeholder="Tarla A" /></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Toprak tipi</label><input type="text" id="ndSoil" placeholder="killi" /></div>
                <div class="form-group"><label>Alan (ha)</label><input type="number" id="ndArea" step="0.1" placeholder="3.5" /></div>
            </div>
            <button class="btn-primary" data-action="submitNewField">Kaydet</button>
        </div>
    `;

    if (farms.length === 0) {
        // v5-3: empty state cilası — illustration + iki CTA (yeni çiftlik / demo)
        html += `<div class="empty-state">
            <div class="icon">🚜</div>
            <p><strong>Henüz hiç çiftliğin yok.</strong></p>
            <p>İlk çiftliğini ekleyerek başla veya örnek verilerle deneyebilirsin.</p>
            <div class="cta-row">
                <button class="btn-primary" data-action="toggleForm" data-arg="newFarmForm">➕ İlk çiftliğimi ekle</button>
                <button class="btn-link" data-action="loadDemoData">veya demo verisi yükle</button>
            </div>
        </div>`;
        container.innerHTML = html;
        _setBusy('fieldsListContainer', false);
        return;
    }

    // Her çiftliğin detayını çek (nested fields için). Küçük N (farmer 1-4 farm).
    const details = await Promise.all(farms.map(f => apiAuth(`/api/farms/${f.id}`)));
    for (const farm of details) {
        if (!farm) continue;
        const fields = farm.fields || [];
        html += `<div class="farm-group">
            <div class="farm-group-header">
                <span>🚜 ${_escAttr(farm.name)}${farm.city ? ` · ${_escAttr(farm.city)}` : ''}${farm.region ? ` <span class="farm-region">${_escAttr(farm.region)}</span>` : ''}</span>
                <span class="farm-actions">
                    <button class="btn-mini" data-action="editFarm" data-id="${farm.id}" data-name="${_escAttr(farm.name)}">✏️</button>
                    <button class="btn-mini btn-danger" data-action="deleteFarm" data-id="${farm.id}" data-name="${_escAttr(farm.name)}">🗑</button>
                </span>
            </div>`;
        if (fields.length === 0) {
            html += '<p class="farm-no-fields">Bu çiftlikte tarla kaydı yok.</p>';
        } else {
            html += '<div class="field-cards">';
            for (const f of fields) {
                const area = f.area_hectares != null ? `${_fmtNumber(f.area_hectares)} ha` : '—';
                html += `<div class="field-card-wrap">
                    <a class="field-card" href="#field/${f.id}" data-action="openFieldDetail" data-id="${f.id}">
                        <div class="field-card-name">🌱 ${_escAttr(f.name)}</div>
                        <div class="field-card-meta">${_escAttr(f.soil_type || 'toprak —')} · ${area}</div>
                        <div class="field-card-cta">Detayı gör →</div>
                    </a>
                    <button class="btn-mini btn-danger field-card-del" data-action="deleteField" data-id="${f.id}" data-name="${_escAttr(f.name)}" title="Tarlayı sil">🗑</button>
                </div>`;
            }
            html += '</div>';
        }
        html += '</div>';
    }
    container.innerHTML = html;
    _setBusy('fieldsListContainer', false);
}

// ─── Çiftlik/Tarla CRUD aksiyonları (REBUILD Faz 4) ───────────
export function toggleForm(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

export async function submitNewFarm() {
    const name = document.getElementById('nfName').value.trim();
    if (!name) { showToast('Çiftlik adı gerekli', 'warning'); return; }
    const body = {
        name,
        city: document.getElementById('nfCity').value.trim() || null,
        region: document.getElementById('nfRegion').value.trim() || null,
        area_hectares: parseFloat(document.getElementById('nfArea').value) || null,
    };
    const res = await apiAuth('/api/farms/', { method: 'POST', body: JSON.stringify(body) });
    if (res) { showToast('Çiftlik eklendi ✅', 'success'); loadFields(); }
}

export async function submitNewField() {
    const farmId = parseInt(document.getElementById('ndFarm').value, 10);
    const name = document.getElementById('ndName').value.trim();
    if (!farmId || !name) { showToast('Çiftlik ve tarla adı gerekli', 'warning'); return; }
    const body = {
        farm_id: farmId,
        name,
        soil_type: document.getElementById('ndSoil').value.trim() || null,
        area_hectares: parseFloat(document.getElementById('ndArea').value) || null,
    };
    const res = await apiAuth('/api/fields', { method: 'POST', body: JSON.stringify(body) });
    if (res) { showToast('Tarla eklendi ✅', 'success'); loadFields(); }
}

export async function editFarm(farmId, currentName) {
    const name = prompt('Yeni çiftlik adı:', currentName);
    if (name === null) return;
    if (!name.trim()) { showToast('Ad boş olamaz', 'warning'); return; }
    const res = await apiAuth(`/api/farms/${farmId}`, { method: 'PATCH', body: JSON.stringify({ name: name.trim() }) });
    if (res) { showToast('Çiftlik güncellendi', 'success'); loadFields(); }
}

export async function deleteFarm(farmId, name) {
    if (!confirm(`"${name}" çiftliğini silmek istiyor musun? (Tarlası varsa silinemez.)`)) return;
    const token = getAuthToken();
    try {
        const resp = await fetch(`${API_BASE}/api/farms/${farmId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.status === 204) { showToast('Çiftlik silindi', 'success'); loadFields(); }
        else { const e = await resp.json().catch(() => ({})); showToast(e.detail || `Silinemedi (${resp.status})`, 'error'); }
    } catch { showToast('Sunucuya ulaşılamadı', 'error'); }
}

export async function editField(fieldId, currentName) {
    const name = prompt('Yeni tarla adı:', currentName);
    if (name === null) return;
    if (!name.trim()) { showToast('Ad boş olamaz', 'warning'); return; }
    const res = await apiAuth(`/api/fields/${fieldId}`, { method: 'PATCH', body: JSON.stringify({ name: name.trim() }) });
    if (res) { showToast('Tarla güncellendi', 'success'); if (currentFieldId === fieldId) loadFieldDetail(fieldId); else loadFields(); }
}

export async function deleteField(fieldId, name) {
    if (!confirm(`"${name}" tarlasını silmek istiyor musun? (Sensörü varsa silinemez.)`)) return;
    const token = getAuthToken();
    try {
        const resp = await fetch(`${API_BASE}/api/fields/${fieldId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.status === 204) {
            showToast('Tarla silindi', 'success');
            // Detay sayfasındaysak listeye dön
            if (currentFieldId === fieldId) { location.hash = '#fields'; window.dispatchEvent(new CustomEvent('navigate', { detail: 'fields' })); }
            else loadFields();
        } else { const e = await resp.json().catch(() => ({})); showToast(e.detail || `Silinemedi (${resp.status})`, 'error'); }
    } catch { showToast('Sunucuya ulaşılamadı', 'error'); }
}

// ─── Sensör CRUD (fixroll_v2 #7) ─────────────────────────────
export async function submitNewSensor(fieldId) {
    const sensor_type = document.getElementById('nsType').value;
    const serial_number = document.getElementById('nsSerial').value.trim();
    if (!serial_number) { showToast('Seri no gerekli', 'warning'); return; }
    const body = {
        field_id: fieldId,
        sensor_type,
        serial_number,
        depth_cm: parseFloat(document.getElementById('nsDepth').value) || null,
    };
    const res = await apiAuth('/api/sensors/', { method: 'POST', body: JSON.stringify(body) });
    if (res) {
        showToast('Sensör eklendi ✅', 'success');
        if (currentFieldId) loadFieldDetail(currentFieldId);
    }
}

export async function deleteSensor(sensorId, label) {
    if (!confirm(`"${label}" sensörünü silmek istiyor musun? Bu işlem geri alınamaz.`)) return;
    const token = getAuthToken();
    try {
        const resp = await fetch(`${API_BASE}/api/sensors/${sensorId}`, {
            method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }
        });
        // sensors.py DELETE 200 dönüyor (farms/fields 204) — evrensel success check
        if (resp.ok) {
            showToast('Sensör silindi', 'success');
            if (currentFieldId) loadFieldDetail(currentFieldId);
        } else {
            const e = await resp.json().catch(() => ({}));
            showToast(e.detail || `Silinemedi (${resp.status})`, 'error');
        }
    } catch { showToast('Sunucuya ulaşılamadı', 'error'); }
}

// ─── TARLA DETAYI (FIELD DETAIL) ──────────────────────────────
let currentFieldId = null;

export function openFieldDetail(fieldId) {
    currentFieldId = fieldId;
    // Sayfayı aktive et (navigate yerine doğrudan — parametrik route).
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => { n.classList.remove('active'); n.removeAttribute('aria-current'); });
    document.getElementById('page-field-detail').classList.add('active');
    document.getElementById('pageTitle').textContent = pageTitles['field-detail'][0];
    document.getElementById('pageSubtitle').textContent = pageTitles['field-detail'][1];
    if (location.hash !== `#field/${fieldId}`) location.hash = `#field/${fieldId}`;
    const main = document.getElementById('main-content');
    if (main) main.focus({ preventScroll: false });
    loadFieldDetail(fieldId);
}

async function loadFieldDetail(fieldId) {
    const c = document.getElementById('fieldDetailContainer');
    c.innerHTML = _skeletonBlock(5);
    _setBusy('fieldDetailContainer', true);
    const data = await apiAuth(`/api/fields/${fieldId}`);
    if (!data) {
        c.innerHTML = '<div class="empty-state"><p>⚠️ Tarla detayı alınamadı (erişim yok veya bulunamadı).</p></div>';
        _setBusy('fieldDetailContainer', false);
        return;
    }
    c.innerHTML = renderFieldDetail(data);
    _setBusy('fieldDetailContainer', false);
    // Nem trend grafiği (ayrı endpoint)
    loadFieldReadingsChart(fieldId);
}

function renderFieldDetail(d) {
    const cropName = d.crop ? d.crop.name : 'Ekili bitki yok';
    const moistVal = d.avg_moisture_percent != null ? `%${_fmtNumber(d.avg_moisture_percent)}` : '—';
    const ms = d.moisture_status || 'no_data';

    // Sensör kartları — hover'da 🗑 sil butonu (fixroll_v2 #7)
    const sensorRows = (d.sensors || []).map(s => {
        const m = s.latest_moisture_percent != null ? `%${_fmtNumber(s.latest_moisture_percent)}` : '—';
        const t = s.latest_soil_temperature_c != null ? `${_fmtNumber(s.latest_soil_temperature_c)}°C` : '—';
        const label = `${s.sensor_type}${s.serial_number ? ' (' + s.serial_number + ')' : ''}`;
        return `<div class="detail-mini-card sensor-card-wrap">
            <div class="detail-mini-title">📡 ${_escAttr(s.sensor_type)} <span class="sensor-status sensor-${_escAttr(s.status)}">${_escAttr(s.status)}</span></div>
            <div class="detail-mini-row">Nem: <strong>${m}</strong> · Toprak: <strong>${t}</strong></div>
            <div class="detail-mini-sub">${s.latest_reading_at ? _fmtDate(s.latest_reading_at) : 'okuma yok'}</div>
            <button class="btn-mini btn-danger sensor-card-del" data-action="deleteSensor" data-id="${s.id}" data-name="${_escAttr(label)}" title="Sensörü sil">🗑</button>
        </div>`;
    }).join('') || '<p class="detail-empty">Bu tarlada sensör yok.</p>';

    // Sulama geçmişi — pending kayıtlarda tamamla/iptal butonları
    const irrRows = (d.recent_irrigations || []).map(i => {
        const amt = i.water_amount_liters != null ? `${_fmtNumber(i.water_amount_liters, 0)} L` : '—';
        const actions = i.status === 'pending'
            ? `<button class="btn-mini" data-action="updateIrrigationStatus" data-id="${i.id}" data-status="completed">✓ Tamamlandı</button>
               <button class="btn-mini btn-danger" data-action="updateIrrigationStatus" data-id="${i.id}" data-status="cancelled">✗ İptal</button>`
            : '—';
        return `<tr><td>${_fmtDate(i.scheduled_date)}</td><td>${amt}</td><td>${i.duration_min ?? '—'} dk</td><td><span class="irr-status irr-${_escAttr(i.status)}">${_escAttr(i.status)}</span></td><td class="user-actions">${actions}</td></tr>`;
    }).join('') || '<tr><td colspan="5" class="detail-empty">Sulama kaydı yok.</td></tr>';

    // Hastalık geçmişi
    const disRows = (d.disease_history || []).map(h => {
        const conf = h.confidence_score != null ? `%${_fmtNumber(h.confidence_score * 100, 0)}` : '—';
        return `<tr><td>${_fmtDate(h.captured_at)}</td><td>${_escAttr(h.diagnosis || '—')}</td><td>${conf}</td><td>${_escAttr(h.severity || '—')}</td></tr>`;
    }).join('') || '<tr><td colspan="4" class="detail-empty">Hastalık analizi yok.</td></tr>';

    // Toprak analizi (en yeni)
    let soilHtml = '<p class="detail-empty">Toprak analizi yok.</p>';
    if ((d.soil_analyses || []).length > 0) {
        const s = d.soil_analyses[0];
        soilHtml = `<div class="detail-mini-row">pH: <strong>${s.ph_level ?? '—'}</strong> · N: <strong>${s.nitrogen_mg_kg ?? '—'}</strong> · P: <strong>${s.phosphorus_mg_kg ?? '—'}</strong> · K: <strong>${s.potassium_mg_kg ?? '—'}</strong> mg/kg</div>
            <div class="detail-mini-sub">${_escAttr(s.texture_class || '')} · ${_fmtDate(s.analysis_date)}</div>`;
    }

    // Açık uyarılar
    const alertRows = (d.open_alerts || []).map(a =>
        `<div class="detail-alert severity-${_escAttr(a.severity)}"><strong>${_escAttr(a.severity)}</strong> · ${_escAttr(a.message)} <span class="detail-mini-sub">${_fmtDate(a.created_at)}</span></div>`
    ).join('') || '<p class="detail-empty">Açık uyarı yok ✅</p>';

    return `
        <div class="hero-banner field-detail-hero">
            <h1><span class="hero-emoji">🌱</span> ${_escAttr(d.name)}</h1>
            <p>🚜 ${_escAttr(d.farm_name)}${d.region ? ` · ${_escAttr(d.region)}` : ''}${d.city ? ` · ${_escAttr(d.city)}` : ''}</p>
            <div class="hero-stats">
                <div class="hero-stat">🌾 ${_escAttr(cropName)}</div>
                <div class="hero-stat">📐 ${d.area_hectares != null ? _fmtNumber(d.area_hectares) + ' ha' : '—'}</div>
                <div class="hero-stat">🪨 ${_escAttr(d.soil_type || '—')}</div>
            </div>
            <div class="field-detail-actions">
                <button class="btn-mini" data-action="editField" data-id="${d.id}" data-name="${_escAttr(d.name)}">✏️ Düzenle</button>
                <button class="btn-mini btn-danger" data-action="deleteField" data-id="${d.id}" data-name="${_escAttr(d.name)}">🗑 Sil</button>
            </div>
        </div>

        <div class="cards-grid">
            <div class="metric-card metric-status-${ms}">
                <div class="metric-head"><span class="metric-icon" aria-hidden="true">💧</span><span class="metric-title">Toprak nemi (son 24 sa.)</span></div>
                <div class="metric-value">${moistVal}</div>
                <div class="metric-status"><span class="metric-status-pill">${_STATUS_EMOJI[ms]} ${_STATUS_LABEL[ms]}</span></div>
            </div>
        </div>

        <div class="section-header">📡 Sensörler
            <button class="btn-mini" style="float:right;" data-action="toggleForm" data-arg="newSensorForm">➕ Sensör Ekle</button>
        </div>
        <div class="form-box crud-form" id="newSensorForm" style="display:none;">
            <div class="form-row">
                <div class="form-group">
                    <label>Tip *</label>
                    <select id="nsType">
                        <option value="soil_moisture">Toprak Nemi</option>
                        <option value="soil_temperature">Toprak Sıcaklığı</option>
                        <option value="humidity">Hava Nemi</option>
                    </select>
                </div>
                <div class="form-group"><label>Seri No *</label><input type="text" id="nsSerial" placeholder="SN-2026-001" /></div>
                <div class="form-group"><label>Derinlik (cm)</label><input type="number" id="nsDepth" value="20" step="1" /></div>
            </div>
            <button class="btn-primary" data-action="submitNewSensor" data-id="${d.id}">Kaydet</button>
        </div>
        <div class="detail-mini-grid">${sensorRows}</div>

        <div class="section-header">📈 Nem Trendi</div>
        <div class="chart-box"><canvas id="fieldReadingsChart"></canvas></div>

        <div class="section-header">🦠 Hastalık Tespiti — Yaprak Fotoğrafı Yükle</div>
        <div class="form-box">
            <div class="form-group">
                <label for="fieldLeafFile">Yaprak Görseli (JPG/PNG/WebP, max 5 MB)</label>
                <input type="file" id="fieldLeafFile" accept="image/jpeg,image/png,image/webp" />
            </div>
            <div id="fieldLeafPreviewWrap" style="display:none;text-align:center;margin:12px 0;">
                <img id="fieldLeafPreview" alt="Önizleme" style="max-width:240px;max-height:180px;border-radius:12px;border:1px solid var(--border);" />
            </div>
            <button class="btn-primary" id="fieldLeafBtn" data-action="analyzeFieldLeaf">🔬 Hastalığı Tespit Et</button>
            <div id="fieldLeafResult" style="display:none;margin-top:16px;"></div>
        </div>

        <div class="section-header">🚿 Sulama Geçmişi
            <button class="btn-mini" style="float:right;" data-action="addFieldIrrigation" data-id="${d.id}">➕ Sulama programı ekle</button>
        </div>
        <div class="table-box"><table class="detail-table"><thead><tr><th>Tarih</th><th>Su</th><th>Süre</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>${irrRows}</tbody></table></div>

        <div class="section-header">🩺 Hastalık Geçmişi</div>
        <div class="table-box"><table class="detail-table"><thead><tr><th>Tarih</th><th>Teşhis</th><th>Güven</th><th>Şiddet</th></tr></thead><tbody>${disRows}</tbody></table></div>

        <div class="section-header">🪨 Toprak Analizi</div>
        <div class="form-box">${soilHtml}</div>

        <div class="section-header">🚨 Açık Uyarılar</div>
        <div>${alertRows}</div>
    `;
}

async function loadFieldReadingsChart(fieldId) {
    const readings = await apiAuth(`/api/fields/${fieldId}/readings?limit=50`);
    const canvas = document.getElementById('fieldReadingsChart');
    if (!canvas || !readings) return;
    const labels = readings.map(r => new Date(r.reading_timestamp).toLocaleDateString('tr'));
    const values = readings.map(r => r.moisture_percent);
    if (fieldReadingsChart) fieldReadingsChart.destroy();
    fieldReadingsChart = new Chart(canvas, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Nem %', data: values, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,.1)', fill: true, tension: .4, pointRadius: 2 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
}

// Tarla detayında yaprak foto upload — field_id sabit (currentFieldId).
export async function analyzeFieldLeaf() {
    const fileInput = document.getElementById('fieldLeafFile');
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        showToast('Lütfen bir görsel seç', 'warning');
        return;
    }
    const file = fileInput.files[0];
    if (file.size > 5 * 1024 * 1024) { showToast('Dosya 5 MB\'dan büyük', 'error'); return; }
    const token = getAuthToken();
    if (!token) { showToast('Giriş yapman gerekiyor', 'warning'); location.hash = '#auth'; return; }
    const btn = document.getElementById('fieldLeafBtn');
    btn.disabled = true; btn.textContent = '⏳ Analiz ediliyor...';
    const fd = new FormData();
    fd.append('field_id', currentFieldId);
    fd.append('image', file);
    try {
        const resp = await fetch(`${API_BASE}/api/plants/health-images/analyze`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: fd,
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            showToast(err.detail || `Hata ${resp.status}`, 'error');
            return;
        }
        const data = await resp.json();
        const sev = data.severity || 'none';
        const sevColor = sev === 'severe' ? '#ef4444' : sev === 'moderate' ? '#f97316' : sev === 'mild' ? '#eab308' : '#22c55e';
        const box = document.getElementById('fieldLeafResult');
        box.innerHTML = `<div style="border-left:4px solid ${sevColor};padding-left:12px;">
            <h4 style="margin:0 0 6px;">🧪 ${_escAttr(data.diagnosis)}</h4>
            <p style="margin:2px 0;">Güven: <strong>%${_fmtNumber(data.confidence_score * 100, 0)}</strong> · Şiddet: <strong style="color:${sevColor};">${_escAttr(sev)}</strong></p>
        </div>`;
        box.style.display = 'block';
        showToast('Analiz tamamlandı ✅', 'success');
        // Detayı yenile — hastalık geçmişine yeni kayıt düşsün.
        loadFieldDetail(currentFieldId);
    } catch (e) {
        showToast('Sunucuya ulaşılamadı', 'error');
    } finally {
        btn.disabled = false; btn.textContent = '🔬 Hastalığı Tespit Et';
    }
}

// Dinamik yenileme (örneğin irrigation modülünden sulama programı eklenince detay yenilensin)
window.addEventListener('refreshFieldDetail', () => {
    if (currentFieldId) loadFieldDetail(currentFieldId);
});
