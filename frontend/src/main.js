/* ============================================================
   SFDAP Dashboard — Entry Point (Orchestrator)
   ============================================================
   Refactored: API, utils, router modülleri `src/lib/` altında.
   Bu dosya state yönetimi + page handler'ları + window bridge.

   `<script type="module">` ile yüklenir. Inline `onclick`
   handler'lar `window` global'ine ihtiyaç duyar — dosyanın sonunda
   tüm public function'lar `window.X = X` ile expose edilir.
   ============================================================ */

import { _skeletonBlock, _skeletonCards, _skeletonRows, _setBusy } from "./lib/skeleton.js";
import { loadMap as _loadMapImpl } from "./lib/map.js";
import {
    api, apiAuth, API_BASE, AUTH_TOKEN_KEY,
    getAuthToken, setAuthToken, clearAuthToken,
    _authHeaders, initApiCallbacks,
} from "./lib/api.js";
import { _fmtDate, _fmtNumber, _escAttr, showToast, updateStatus, updateClock, _STATUS_EMOJI, _STATUS_LABEL } from "./lib/utils.js";
import { pageTitles, navigate as _navigateCore, toggleSidebar, initHashRouter } from "./lib/router.js";
import { charts, renderMoistureChart, renderTempHumChart, renderPrecipChart,
         renderSensorTypeChart, renderFarmTempChart, renderIrrigationStatusChart,
         renderNpkRadarChart, renderDailyTrendChart, renderSensorStatsChart } from "./lib/charts.js";
import { renderFieldDetail, renderPlantResult } from "./lib/render.js";
let refreshInterval = null;
let apiOnline = false;
// Son /me snapshot — header badge + role-aware UI guard'ları için.
// Login/logout sırasında refreshAuthState() bu objeyi güncelliyor.
let currentUser = null;




// ─── NAVIGATION (delegates to lib/router.js) ─────────────────
// Page handler map — navigate() çağrıldığında doğru veri-yükleme fonksiyonunu çalıştırır.
const pageHandlers = {
    dashboard: () => loadDashboard(),
    fields: () => loadFields(),
    sensors: () => loadSensors(),
    weather: () => loadWeather(),
    irrigation: () => loadIrrigation(),
    analytics: () => loadAnalytics(),
    map: () => loadMap(),
    plants: () => loadPlants(),
    alerts: () => loadAlerts(),
    users: () => loadUsers(),
    auth: () => refreshAuthState(),
};

function navigate(page) {
    _navigateCore(page, pageHandlers, _startHeroTipRotation);
}

// Hash router'ı init'te başlatacağız (init fonksiyonunda).


// ─── DASHBOARD ────────────────────────────────────────────────
// REBUILD Faz 2 / Adım 8: "Çiftliğim" rol-aware kartlar
// /api/dashboard/summary tek endpoint'inden 4 metrik card + hero stats
// + trend chart'ları (Bearer-aware api() üzerinden).





function _renderSummaryCards(summary) {
    const moist = summary.soil_moisture_today || {};
    const irr = summary.last_irrigation || {};
    const alerts = summary.open_alerts || { by_severity: {} };
    const disease = summary.last_disease || {};
    const scopeNote = summary.scope === 'system'
        ? 'Sistem geneli'
        : 'Senin tarlalarından';
    const moistValue = moist.avg_moisture_percent !== null && moist.avg_moisture_percent !== undefined
        ? `%${_fmtNumber(moist.avg_moisture_percent)}`
        : '—';
    const moistStatus = moist.status || 'no_data';
    const irrAmount = irr.water_amount_liters !== null && irr.water_amount_liters !== undefined
        ? `${_fmtNumber(irr.water_amount_liters, 0)} L`
        : '—';
    const irrTitle = irr.field_name ? `${irr.field_name} · ${_fmtDate(irr.scheduled_date)}` : 'Sulama kaydı yok';
    const sev = alerts.by_severity || {};
    const severityChips = [
        { key: 'critical', label: 'kritik', cls: 'critical' },
        { key: 'medium', label: 'orta', cls: 'medium' },
        { key: 'low', label: 'düşük', cls: 'low' },
    ].map(({ key, label, cls }) => {
        const cnt = sev[key] || 0;
        return cnt > 0
            ? `<span class="severity-chip severity-${cls}">${cnt} ${label}</span>`
            : '';
    }).join(' ');
    const diseaseDx = disease.diagnosis || '—';
    const diseaseDetail = disease.diagnosis
        ? `${disease.field_name || 'Tarla'} · ${_fmtDate(disease.captured_at)} · güven %${_fmtNumber((disease.confidence_score || 0) * 100, 0)}`
        : 'Henüz yaprak görseli analiz edilmedi';
    return `
        <div class="metric-card metric-moisture metric-status-${moistStatus}">
            <div class="metric-head">
                <span class="metric-icon" aria-hidden="true">💧</span>
                <span class="metric-title">Bugün toprak nemi</span>
            </div>
            <div class="metric-value">${moistValue}</div>
            <div class="metric-status">
                <span class="metric-status-pill">${_STATUS_EMOJI[moistStatus]} ${_STATUS_LABEL[moistStatus]}</span>
            </div>
            <div class="metric-context">${moist.sensor_count || 0} sensör · ${moist.reading_count || 0} okuma · son 24 sa.</div>
            <div class="metric-scope">${scopeNote}</div>
        </div>

        <div class="metric-card metric-irrigation">
            <div class="metric-head">
                <span class="metric-icon" aria-hidden="true">🚿</span>
                <span class="metric-title">Son sulama</span>
            </div>
            <div class="metric-value">${irrAmount}</div>
            <div class="metric-context"><strong>${_escAttr(irr.field_name || '—')}</strong> · ${_fmtDate(irr.scheduled_date)}</div>
            <div class="metric-context">${_escAttr(irr.status || (irr.irrigation_id ? '—' : 'Sulama kaydı yok'))}</div>
            <div class="metric-scope">${scopeNote}</div>
        </div>

        <div class="metric-card metric-alerts ${alerts.total > 0 ? 'has-alerts' : ''}">
            <div class="metric-head">
                <span class="metric-icon" aria-hidden="true">🚨</span>
                <span class="metric-title">Açık uyarılar</span>
            </div>
            <div class="metric-value">${alerts.total || 0}</div>
            <div class="metric-context metric-severities">${severityChips || '<span class="metric-status-pill">Açık uyarı yok ✅</span>'}</div>
            <div class="metric-context metric-latest">${alerts.latest_message ? _escAttr(alerts.latest_message) : ''}</div>
            <div class="metric-scope">${scopeNote}</div>
        </div>

        <div class="metric-card metric-disease metric-severity-${disease.severity || 'none'}">
            <div class="metric-head">
                <span class="metric-icon" aria-hidden="true">🦠</span>
                <span class="metric-title">Son hastalık tanısı</span>
            </div>
            <div class="metric-value metric-value-text">${_escAttr(diseaseDx)}</div>
            <div class="metric-context">${_escAttr(diseaseDetail)}</div>
            <div class="metric-scope">${scopeNote}</div>
        </div>
    `;
}

// Onboarding banner — boş hesap (farm_count==0) için (REBUILD Faz 6)
function _onboardingBannerHtml() {
    return `
        <div class="onboarding-banner" style="grid-column: 1 / -1;">
            <div class="onboarding-emoji" aria-hidden="true">🌱</div>
            <h3>Hoş geldin! Hadi başlayalım.</h3>
            <p>Henüz çiftliğin yok. İlk çiftliğini ekleyerek başlayabilir ya da
               tek tıkla örnek verilerle platformu hemen keşfedebilirsin.</p>
            <div class="onboarding-actions">
                <button class="btn-primary" data-action="addFirstFarm">➕ İlk çiftliğimi ekle</button>
                <button class="btn-secondary" id="loadDemoBtn" data-action="loadDemoData">🎬 Demo verisi yükle</button>
            </div>
        </div>`;
}

/** Tek-tık demo veri kur (POST /api/onboarding/demo) → dashboard'u tazele. */
async function loadDemoData() {
    const btn = document.getElementById('loadDemoBtn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Kuruluyor...'; }
    const res = await apiAuth('/api/onboarding/demo', { method: 'POST' });
    if (res) {
        showToast('Demo verisi kuruldu ✅ — keşfetmeye başla!', 'success');
        await refreshAuthState();  // badge owned_farms_count + bell tazele
        loadDashboard();
    } else if (btn) {
        btn.disabled = false; btn.textContent = '🎬 Demo verisi yükle';
    }
}

async function loadDashboard() {
    const cards = document.getElementById('dashboardCards');
    cards.innerHTML = _skeletonCards(4);
    _setBusy('dashboardCards', true);

    // Token yoksa rol-aware özet çekilmez; kullanıcıyı auth sayfasına yönlendir.
    const token = getAuthToken();
    if (!token) {
        cards.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <p>🔐 "Çiftliğim" özetini görmek için <a href="#auth">giriş yap</a>.</p>
            </div>
        `;
        _setBusy('dashboardCards', false);
        updateStatus(apiOnline);
        return;
    }

    const [summary, weather] = await Promise.all([
        apiAuth('/api/dashboard/summary'),
        api('/api/weather/?limit=30'),
    ]);
    apiOnline = summary !== null;
    updateStatus(apiOnline);

    if (summary && summary.scope === 'user' && summary.farm_count === 0) {
        // Boş hesap — onboarding banner (REBUILD Faz 6)
        cards.innerHTML = _onboardingBannerHtml();
        const heroFarms = document.getElementById('heroFarms');
        if (heroFarms) heroFarms.textContent = '0';
    } else if (summary) {
        cards.innerHTML = _renderSummaryCards(summary);
        // Hero stats — rol-aware sayım. Farmer için "kendi" çiftlik/sensör;
        // admin için sistem geneli.
        const heroFarms = document.getElementById('heroFarms');
        const heroSensors = document.getElementById('heroSensors');
        const heroReadings = document.getElementById('heroReadings');
        if (heroFarms) heroFarms.textContent = summary.farm_count;
        if (heroSensors) heroSensors.textContent = summary.sensor_count;
        if (heroReadings) heroReadings.textContent = (summary.soil_moisture_today || {}).reading_count || 0;
    } else {
        cards.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <p>⚠️ Özet alınamadı. <button class="btn-link" data-action="loadDashboard">Tekrar dene</button></p>
            </div>
        `;
    }
    _setBusy('dashboardCards', false);

    // Trend chart'lar — weather Bearer üzerinden gelir (api() artık _authHeaders kullanıyor).
    const w = weather || [];
    renderMoistureChart(w);
    renderTempHumChart(w);
    renderPrecipChart(w);
}

// ─── TARLALARIM (FIELD LIST) ──────────────────────────────────
// REBUILD Faz 3 / Adım 6: çiftlik bazlı tarla listesi.
// /api/farms/ → her farm için /api/farms/{id} (nested fields).
// Tarlalarım sayfasında çiftlik dropdown'ı için son çekilen çiftlik listesi
let _myFarms = [];

async function loadFields() {
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
function toggleForm(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

async function submitNewFarm() {
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

async function submitNewField() {
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

async function editFarm(farmId, currentName) {
    const name = prompt('Yeni çiftlik adı:', currentName);
    if (name === null) return;
    if (!name.trim()) { showToast('Ad boş olamaz', 'warning'); return; }
    const res = await apiAuth(`/api/farms/${farmId}`, { method: 'PATCH', body: JSON.stringify({ name: name.trim() }) });
    if (res) { showToast('Çiftlik güncellendi', 'success'); loadFields(); }
}

async function deleteFarm(farmId, name) {
    if (!confirm(`"${name}" çiftliğini silmek istiyor musun? (Tarlası varsa silinemez.)`)) return;
    const token = getAuthToken();
    try {
        const resp = await fetch(`${API_BASE}/api/farms/${farmId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.status === 204) { showToast('Çiftlik silindi', 'success'); loadFields(); }
        else { const e = await resp.json().catch(() => ({})); showToast(e.detail || `Silinemedi (${resp.status})`, 'error'); }
    } catch { showToast('Sunucuya ulaşılamadı', 'error'); }
}

async function editField(fieldId, currentName) {
    const name = prompt('Yeni tarla adı:', currentName);
    if (name === null) return;
    if (!name.trim()) { showToast('Ad boş olamaz', 'warning'); return; }
    const res = await apiAuth(`/api/fields/${fieldId}`, { method: 'PATCH', body: JSON.stringify({ name: name.trim() }) });
    if (res) { showToast('Tarla güncellendi', 'success'); if (currentFieldId === fieldId) loadFieldDetail(fieldId); else loadFields(); }
}

async function deleteField(fieldId, name) {
    if (!confirm(`"${name}" tarlasını silmek istiyor musun? (Sensörü varsa silinemez.)`)) return;
    const token = getAuthToken();
    try {
        const resp = await fetch(`${API_BASE}/api/fields/${fieldId}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.status === 204) {
            showToast('Tarla silindi', 'success');
            // Detay sayfasındaysak listeye dön
            if (currentFieldId === fieldId) { location.hash = '#fields'; navigate('fields'); }
            else loadFields();
        } else { const e = await resp.json().catch(() => ({})); showToast(e.detail || `Silinemedi (${resp.status})`, 'error'); }
    } catch { showToast('Sunucuya ulaşılamadı', 'error'); }
}

// ─── Sensör CRUD (fixroll_v2 #7) ─────────────────────────────
async function submitNewSensor(fieldId) {
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

async function deleteSensor(sensorId, label) {
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

function openFieldDetail(fieldId) {
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


async function loadFieldReadingsChart(fieldId) {
    const readings = await apiAuth(`/api/fields/${fieldId}/readings?limit=50`);
    const canvas = document.getElementById('fieldReadingsChart');
    if (!canvas || !readings) return;
    const labels = readings.map(r => new Date(r.reading_timestamp).toLocaleDateString('tr'));
    const values = readings.map(r => r.moisture_percent);
    if (charts.fieldReadings) charts.fieldReadings.destroy();
    charts.fieldReadings = new Chart(canvas, {
        type: 'line',
        data: { labels, datasets: [{ label: 'Nem %', data: values, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,.1)', fill: true, tension: .4, pointRadius: 2 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
}

// Tarla detayında yaprak foto upload — field_id sabit (currentFieldId).
async function analyzeFieldLeaf() {
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




// ─── SENSORS ──────────────────────────────────────────────────
// Pagination: sayfa basi 50 kayit, slider ile sayfalari gez.
const PAGE_SIZE = 50;
let sensorsPage = 1;
let sensorsTotal = 0;

async function loadSensors(page = 1) {
    // Table skeleton — 6 rows × 4 columns before the fetch returns.
    document.getElementById('sensorsTable').innerHTML = _skeletonRows(6, 4);
    _setBusy('sensorsTable', true);
    // Toplam sayiyi her sayfa degisikliginde tekrar cekmek pahali —
    // ilk yuklemede al, sonra cache'le. Yeni sensor eklenirse sayfa
    // degistiginde tekrar fetch edilir (bilincli trade-off).
    if (sensorsTotal === 0) {
        const cnt = await api('/api/sensors/count');
        sensorsTotal = cnt?.total || 0;
    }
    const totalPages = Math.max(1, Math.ceil(sensorsTotal / PAGE_SIZE));
    sensorsPage = Math.min(Math.max(1, page), totalPages);
    const skip = (sensorsPage - 1) * PAGE_SIZE;

    const sensors = await api(`/api/sensors/?skip=${skip}&limit=${PAGE_SIZE}`) || [];

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
    document.getElementById('sensorsTable').innerHTML = sensors.map(s => `
        <tr tabindex="0" role="button" aria-label="Sensör ${s.id} (${s.sensor_type}) detayını aç"
            style="cursor:pointer" data-action="loadSensorDetail" data-id="${s.id}">
            <td>${s.id}</td><td>${s.sensor_type}</td><td>${s.serial_number}</td>
            <td><span class="badge active">${s.status}</span></td>
        </tr>
    `).join('');
    _setBusy('sensorsTable', false);
}

async function loadSensorDetail(sensorId) {
    const readings = await api(`/api/sensors/${sensorId}/readings?limit=30`) || [];
    const sorted = [...readings].reverse();
    if (charts.sensorDetail) charts.sensorDetail.destroy();
    charts.sensorDetail = new Chart(document.getElementById('sensorDetailChart'), {
        type: 'line', data: { labels: sorted.map(r => new Date(r.reading_timestamp).toLocaleDateString('tr')),
            datasets: [{ label: 'Nem %', data: sorted.map(r => r.moisture_percent), borderColor: '#10b981',
                backgroundColor: 'rgba(16,185,129,.1)', fill: true, tension: .4 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
    document.getElementById('sensorInfoBox').innerHTML = `<h3>ℹ️ Sensör #${sensorId}</h3>
        <p style="margin:12px 0;color:var(--text-muted)">Toplam ${readings.length} okuma</p>
        ${readings.length ? `<p>Son okuma: <strong>%${readings[0].moisture_percent}</strong></p>
        <p>Son sıcaklık: <strong>${readings[0].soil_temperature_c || '—'}°C</strong></p>` : '<p>Veri yok</p>'}`;
}

// ─── WEATHER ──────────────────────────────────────────────────
async function loadWeather() {
    document.getElementById('weatherCards').innerHTML = _skeletonCards(4);
    _setBusy('weatherCards', true);
    const data = await api('/api/weather/?limit=30') || [];
    const sorted = [...data].reverse();
    // Cards
    if (data.length) {
        const temps = data.map(d => d.temperature_c).filter(Boolean);
        document.getElementById('weatherCards').innerHTML = `
            <div class="card"><div class="card-icon" aria-hidden="true">🌡️</div><div class="card-value">${data[0].temperature_c?.toFixed(1) || '—'}°C</div><div class="card-label">Güncel Sıcaklık</div></div>
            <div class="card"><div class="card-icon" aria-hidden="true">💧</div><div class="card-value">%${data[0].humidity_percent?.toFixed(1) || '—'}</div><div class="card-label">Güncel Nem</div></div>
            <div class="card"><div class="card-icon" aria-hidden="true">📊</div><div class="card-value">${Math.min(...temps).toFixed(1)}—${Math.max(...temps).toFixed(1)}°C</div><div class="card-label">Sıcaklık Aralığı</div></div>
            <div class="card"><div class="card-icon" aria-hidden="true">🌧️</div><div class="card-value">${data.reduce((a,d) => a + (d.precipitation_mm||0), 0).toFixed(1)}mm</div><div class="card-label">Toplam Yağış</div></div>
        `;
    }
    _setBusy('weatherCards', false);
    // Temperature chart
    const labels = sorted.map(d => new Date(d.recorded_at).toLocaleDateString('tr'));
    if (charts.weatherTemp) charts.weatherTemp.destroy();
    charts.weatherTemp = new Chart(document.getElementById('weatherTempChart'), {
        type: 'line', data: { labels, datasets: [{ label: 'Sıcaklık °C', data: sorted.map(d => d.temperature_c),
            borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.1)', fill: true, tension: .4, pointRadius: 2 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
    // Wind chart
    if (charts.weatherWind) charts.weatherWind.destroy();
    charts.weatherWind = new Chart(document.getElementById('weatherWindChart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Rüzgar km/h', data: sorted.map(d => d.wind_speed_kmh || 0),
            backgroundColor: 'rgba(139,92,246,.4)', borderColor: '#8b5cf6', borderWidth: 1 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
}

// ─── IRRIGATION ───────────────────────────────────────────────
// Pagination: sayfa basi 50 kayit, slider ile sayfalari gez.
let irrigationPage = 1;
let irrigationTotal = 0;

async function loadIrrigation(page = 1) {
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

async function predictIrrigation() {
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
async function approveIrrigation() {
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
async function updateIrrigationStatus(scheduleId, status) {
    const res = await apiAuth(`/api/irrigation/schedules/${scheduleId}/status`, {
        method: 'PATCH', body: JSON.stringify({ status }),
    });
    if (res) {
        showToast(`Sulama durumu: ${status}`, 'success');
        if (currentFieldId) loadFieldDetail(currentFieldId);
    }
}

/** Tarla detayından hızlı sulama programı ekle (bugün, su miktarı sorulur). */
async function addFieldIrrigation(fieldId) {
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
async function recommendFertilizer() {
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
                    <div><div style="font-size:.8rem;color:var(--text-muted)">Azot (N)</div><div style="font-size:1.3rem;font-weight:700;color:#10b981">${r.nitrogen_needed_kg} kg</div></div>
                    <div><div style="font-size:.8rem;color:var(--text-muted)">Fosfor (P)</div><div style="font-size:1.3rem;font-weight:700;color:#3b82f6">${r.phosphorus_needed_kg} kg</div></div>
                    <div><div style="font-size:.8rem;color:var(--text-muted)">Potasyum (K)</div><div style="font-size:1.3rem;font-weight:700;color:#f59e0b">${r.potassium_needed_kg} kg</div></div>
                </div>
                <p style="color:var(--text-muted);font-size:.85rem;">${r.recommendation}</p>
            </div>`;
        showToast('Gübreleme önerisi hazır', 'success');
    }
}

async function fertilizerSchedule() {
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
    }
}

// ─── ANALYTICS ─────────────────────────────────────────────────

async function loadAnalytics() {
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
async function loadMap() {
    return _loadMapImpl({ api });
}

// ─── PLANTS (BİTKİ SAĞLIĞI) ───────────────────────────────────
async function loadPlants() {
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

async function analyzePlantImage() {
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

// ─── ALERTS ───────────────────────────────────────────────────
async function loadAlerts() {
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

async function resolveAlert(id) {
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
function _renderUserBadge(user) {
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
function goToLogin() {
    const welcome = document.getElementById('welcome');
    const landing = document.getElementById('landing');
    if (welcome) welcome.style.display = 'none';
    if (landing) landing.style.display = 'flex';
    const email = document.getElementById('loginEmail');
    if (email) email.focus();
}

/** Login formundan welcome'a geri dön. */
function goToWelcome() {
    const welcome = document.getElementById('welcome');
    const landing = document.getElementById('landing');
    if (landing) landing.style.display = 'none';
    if (welcome) welcome.style.display = 'flex';
}

/** Filiz'i topraktan yavaşça çıkar; 3 sn sonra geri gömül. (welcome ekranı)
 *  Konuşma yok — sadece çık/gir animasyonu. Tekrar tıklanırsa süre yenilenir. */
let _filizPopTimer = null;
function popFiliz() {
    const stage = document.getElementById('welcomeStage');
    if (!stage) return;
    stage.classList.add('popped');
    if (_filizPopTimer) clearTimeout(_filizPopTimer);
    _filizPopTimer = setTimeout(() => {
        stage.classList.remove('popped');
        _filizPopTimer = null;
    }, 3000);
}

/**
 * Rol-aware nav görünürlüğü — `[data-role]` taşıyan nav item'ları yalnız
 * eşleşen role gösterir (örn. admin "Kullanıcılar"). user null ise hepsi gizli.
 */
function _applyRoleVisibility(user) {
    document.querySelectorAll('[data-role]').forEach(el => {
        // data-role tek rol ("admin") veya virgüllü çoklu rol ("admin,overseer,developer")
        const roles = (el.getAttribute('data-role') || '').split(',').map(r => r.trim());
        el.style.display = (user && roles.includes(user.role)) ? '' : 'none';
    });
}

/** Landing'de giriş ↔ kayıt formu geçişi. */
function toggleLandingForm(which) {
    const login = document.getElementById('landingLogin');
    const register = document.getElementById('landingRegister');
    if (!login || !register) return;
    login.style.display = which === 'register' ? 'none' : 'block';
    register.style.display = which === 'register' ? 'block' : 'none';
}

async function refreshAuthState() {
    const token = getAuthToken();
    const loggedIn = document.getElementById('authLoggedIn');
    if (!token) {
        currentUser = null;
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
        currentUser = me;
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
        currentUser = null;
        _renderUserBadge(null);
        _applyRoleVisibility(null);
        _applyAuthGate(null);
        _hideBell();
    }
}

// ─── BİLDİRİM ÇANI (REBUILD Faz 5) ────────────────────────────
function _hideBell() {
    const wrap = document.getElementById('notifWrap');
    if (wrap) wrap.style.display = 'none';
    const dd = document.getElementById('notifDropdown');
    if (dd) dd.style.display = 'none';
}

/** Açık uyarıları çek, çan sayısını + dropdown listesini güncelle. */
async function refreshBell() {
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
                        <span class="notif-item-sev">${_escAttr(a.severity)}</span>
                        <button class="btn-mini" data-action="resolveFromBell" data-id="${a.id}">Çöz</button>
                    </div>
                </div>`).join('');
    }
}

function toggleBell() {
    const dd = document.getElementById('notifDropdown');
    const bell = document.getElementById('notifBell');
    if (!dd) return;
    const open = dd.style.display !== 'none' && dd.style.display !== '';
    dd.style.display = open ? 'none' : 'block';
    if (bell) bell.setAttribute('aria-expanded', open ? 'false' : 'true');
    if (!open) refreshBell();  // açarken tazele
}

/** "Kontrol et" — tarlaları tara, uyarı üret, çanı tazele. */
async function runAlertCheck() {
    const res = await apiAuth('/api/alerts/check', { method: 'POST' });
    if (res) {
        showToast(res.created > 0 ? `${res.created} yeni uyarı üretildi` : 'Yeni uyarı yok ✅', res.created > 0 ? 'warning' : 'success');
        refreshBell();
    }
}

/** Çan dropdown'ından uyarı çöz. */
async function resolveFromBell(alertId) {
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

async function doLogin() {
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

async function doRegister() {
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

async function doChangePassword() {
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

async function loadUsers() {
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

async function createUser() {
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

async function changeUserRole(userId, role) {
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

async function resetUserPassword(userId, email) {
    const np = prompt(`${email} için yeni şifre (min 8 karakter):`);
    if (np === null) return;  // iptal
    if (np.length < 8) { showToast('Şifre en az 8 karakter olmalı', 'warning'); return; }
    const res = await apiAuth(`/api/auth/users/${userId}/password`, {
        method: 'PATCH',
        body: JSON.stringify({ new_password: np }),
    });
    if (res) showToast('Şifre sıfırlandı ✅', 'success');
}

async function deleteUser(userId, email) {
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

async function doLogout() {
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

// Status, showToast, updateClock lib/utils.js'den import edildi.

// ─── INIT ─────────────────────────────────────────────────────
async function init() {
    // API modülüne callback'leri bağla (circular dep önlemek için)
    initApiCallbacks({
        showToast,
        renderUserBadge: _renderUserBadge,
        setCurrentUser: (u) => { currentUser = u; },
    });

    // Hash router'ı başlat
    initHashRouter(navigate, openFieldDetail);

    // ─── EVENT DELEGATION ─────────────────────────────────────
    // data-action → handler map. Inline onclick kaldırıldı, CSP uyumlu.
    const actionMap = {
        navigate:           (el) => navigate(el.dataset.arg),
        toggleSidebar:      () => toggleSidebar(),
        toggleBell:         () => toggleBell(),
        toggleLandingForm:  (el) => { toggleLandingForm(el.dataset.arg); },
        goToLogin:          () => goToLogin(),
        goToWelcome:        () => goToWelcome(),
        popFiliz:           () => popFiliz(),
        doLogin:            () => doLogin(),
        doRegister:         () => doRegister(),
        doLogout:           () => doLogout(),
        doChangePassword:   () => doChangePassword(),
        predictIrrigation:  () => predictIrrigation(),
        recommendFertilizer:() => recommendFertilizer(),
        fertilizerSchedule: () => fertilizerSchedule(),
        analyzePlantImage:  () => analyzePlantImage(),
        runAlertCheck:      () => runAlertCheck(),
        createUser:         () => createUser(),
        loadAlerts:         () => loadAlerts(),
        sensorsPrev:        () => loadSensors(sensorsPage - 1),
        sensorsNext:        () => loadSensors(sensorsPage + 1),
        irrigationPrev:     () => loadIrrigation(irrigationPage - 1),
        irrigationNext:     () => loadIrrigation(irrigationPage + 1),
        // ─── v9a: window-bridge'den taşınan dinamik handler'lar ───────
        // Argümanlar data-* attribute'lerinden okunur (data-id sayı,
        // data-name/data-status/data-arg string). Eski inline onclick'ler
        // template string'lerden data-action'a çevrildi; window global yok.
        openFieldDetail:        (el) => openFieldDetail(+el.dataset.id),
        loadSensorDetail:       (el) => loadSensorDetail(+el.dataset.id),
        addFieldIrrigation:     (el) => addFieldIrrigation(+el.dataset.id),
        resolveAlert:           (el) => resolveAlert(+el.dataset.id),
        resolveFromBell:        (el) => resolveFromBell(+el.dataset.id),
        submitNewSensor:        (el) => submitNewSensor(+el.dataset.id),
        analyzeFieldLeaf:       () => analyzeFieldLeaf(),
        approveIrrigation:      () => approveIrrigation(),
        loadDashboard:          () => loadDashboard(),
        loadDemoData:           () => loadDemoData(),
        submitNewFarm:          () => submitNewFarm(),
        submitNewField:         () => submitNewField(),
        toggleForm:             (el) => toggleForm(el.dataset.arg),
        deleteFarm:             (el) => deleteFarm(+el.dataset.id, el.dataset.name),
        deleteField:            (el) => deleteField(+el.dataset.id, el.dataset.name),
        deleteSensor:           (el) => deleteSensor(+el.dataset.id, el.dataset.name),
        deleteUser:             (el) => deleteUser(+el.dataset.id, el.dataset.name),
        editFarm:               (el) => editFarm(+el.dataset.id, el.dataset.name),
        editField:              (el) => editField(+el.dataset.id, el.dataset.name),
        resetUserPassword:      (el) => resetUserPassword(+el.dataset.id, el.dataset.name),
        updateIrrigationStatus: (el) => updateIrrigationStatus(+el.dataset.id, el.dataset.status),
        // changeUserRole: <select> change event'i — yeni rol el.value'dan okunur
        changeUserRole:         (el) => changeUserRole(+el.dataset.id, el.value),
        // Bileşik aksiyon: boş-durum "İlk çiftliğimi ekle" (navigate + form aç)
        addFirstFarm:           () => { navigate('fields'); toggleForm('newFarmForm'); },
    };

    document.addEventListener('click', (e) => {
        const el = e.target.closest('[data-action]');
        if (!el) return;
        const action = el.dataset.action;
        const handler = actionMap[action];
        if (handler) {
            e.preventDefault();
            handler(el);
        }
    });

    // Select (onchange) delegation — alert filtre dropdown'ları + changeUserRole
    document.addEventListener('change', (e) => {
        const el = e.target.closest('[data-action]');
        if (!el) return;
        const handler = actionMap[el.dataset.action];
        if (handler) handler(el);
    });

    // Keydown delegation — klavye a11y: role="button" taşıyan data-action
    // elemanlarında (örn. sensör satırı) Enter/Space tıklama gibi davranır.
    // v9a: inline onkeydown kaldırıldı, window-bridge'siz event delegation.
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const el = e.target.closest('[data-action][role="button"]');
        if (!el) return;
        const handler = actionMap[el.dataset.action];
        if (handler) {
            e.preventDefault();
            handler(el);
        }
    });

    // Health check
    const health = await api('/api/health');
    apiOnline = health !== null;
    updateStatus(apiOnline);
    if (apiOnline) showToast('Sistem aktif — veriler güncel', 'success');
    else showToast('Bağlantı yok — son kayıtlı veriler gösteriliyor', 'error');

    // Auth state ilk yükleme — gate uygular (login yoksa landing, app gizli).
    await refreshAuthState();

    // REBUILD Faz 3.5: girişsizse hiçbir sayfaya navigate etme — landing kalır.
    // Giriş yapılınca doLogin() navigate('dashboard') çağırır.
    if (currentUser) {
        const raw = location.hash.slice(1) || 'dashboard';
        if (raw.startsWith('field/')) {
            const id = parseInt(raw.split('/')[1], 10);
            if (Number.isFinite(id)) openFieldDetail(id);
            else navigate('dashboard');
        } else if (pageTitles[raw]) {
            navigate(raw);
        } else {
            navigate('dashboard');
        }
    }

    // Auto-refresh every 30s
    refreshInterval = setInterval(() => {
        const activePage = document.querySelector('.page.active')?.id?.replace('page-', '');
        if (activePage === 'dashboard') loadDashboard();
    }, 30000);

    // Clock
    updateClock();
    setInterval(updateClock, 1000);

    // Hero sayılarına count-up animasyonu (sevimlilik pack)
    animateHeroStats();

    // Filiz maskotu
    initFiliz();

    // Tema (light/dark)
    initTheme();
}

/* ─── ✨ Sayı sayma animasyonu (count-up) ─────────────────── */
function animateCount(el, duration = 1400) {
    const target = parseInt((el.textContent || '0').replace(/[^\d]/g, ''), 10);
    if (!Number.isFinite(target) || target === 0) return;
    const start = performance.now();
    el.textContent = '0';
    const tick = (now) => {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - t, 3);   // easeOutCubic — soft sonlanma
        el.textContent = Math.round(target * eased).toLocaleString('tr-TR');
        if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
}
function animateHeroStats() {
    ['heroFarms', 'heroSensors', 'heroReadings'].forEach(id => {
        const el = document.getElementById(id);
        if (el) animateCount(el);
    });
}

/* ─── 🌗 TEMA YÖNETİMİ ───────────────────────────────────── */
function initTheme() {
    const STORAGE_KEY = 'sfdap-theme';
    const root = document.documentElement;
    // Birden çok toggle: header (#themeToggle) + welcome (.welcome-sun / .welcome-moon).
    // Hepsi `.js-theme-toggle` class'ı taşır ve aynı state'i paylaşır.
    const btns = Array.from(document.querySelectorAll('.js-theme-toggle'));
    if (!btns.length) return;

    // İlk tema: localStorage > sistem tercihi > dark default
    const stored = localStorage.getItem(STORAGE_KEY);
    const prefersLight = window.matchMedia?.('(prefers-color-scheme: light)').matches;
    const initial = stored || (prefersLight ? 'light' : 'dark');
    applyTheme(initial);

    btns.forEach(btn => btn.addEventListener('click', () => {
        const current = root.dataset.theme || 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
        localStorage.setItem(STORAGE_KEY, next);
        // Sayfa yeniden yüklenmiyor — toast bildirimi çıkmasın diye.
        // Chart.js renkleri mevcut sayfada eski temada kalır; sayfa değişince güncellenir.
    }));

    function applyTheme(theme) {
        const label = theme === 'light' ? 'Karanlık temaya geç' : 'Aydınlık temaya geç';
        if (theme === 'light') root.dataset.theme = 'light';
        else delete root.dataset.theme;
        btns.forEach(btn => {
            btn.setAttribute('aria-label', label);
            btn.setAttribute('title', label);
        });
    }
}

/* ─── 🌱 FİLİZ MASKOTU ─────────────────────────────────────── */

// Filiz farmer ipucu havuzu — sulama/gübre/ekim/hava/hastalık/hasat/sensör.
// (Item 8b: rol-aware havuzlar; overseer/admin/developer aşağıda; _getRoleTips
//  ile seçilir. Anonim/login-yok durumda farmer havuzu fallback olarak kullanılır.)
const FILIZ_TIPS_FARMER = [
    // ─── 💧 SULAMA ─────────────────────────────────────────────
    {msg: "Toprak nemi %30 altına düştüyse bitki susamış demektir, hemen su ver.", emoji: "💧"},
    {msg: "Akşamüstü veya sabah erken sulama yap — gündüz buharlaşma çok yüksek.", emoji: "🌅"},
    {msg: "Yapraklara değil toprağa su ver — ıslak yaprak hastalık çağırır.", emoji: "🍃"},
    {msg: "Damla sulama %30-50 daha az su tüketir, yatırımına kısa sürede değer.", emoji: "♻️"},
    {msg: "Yağmurdan sonra 1-2 gün sulama yapma — toprak zaten doymuştur.", emoji: "🌧️"},
    {msg: "Köklü bitkilere az ve derin sulama yap; sığ sulama kökü yüzeye çeker.", emoji: "🪴"},
    {msg: "Soğuk suyla sulama bitkiyi şoklar — su, hava sıcaklığına yakın olmalı.", emoji: "🥶"},
    {msg: "Tuzlu kuyu suyunu yağmur suyuyla seyret — toprağa zarar vermesin.", emoji: "🧂"},

    // ─── 🌱 GÜBRELEME & TOPRAK ────────────────────────────────
    {msg: "Gübrelemeden önce mutlaka pH ölç — 6.0-7.0 çoğu bitki için ideal.", emoji: "🧪"},
    {msg: "Aşırı azot bitkiyi tatlı meyve yerine bol yaprak yapmaya iter — dengeli kullan.", emoji: "⚖️"},
    {msg: "Çay asit toprak sever (pH 4.5-6.0), patates de hafif asitten hoşlanır.", emoji: "🍵"},
    {msg: "Hasat öncesi son gübrelemeyi 30 gün önce kes — meyve/tane sağlıklı olgunlaşsın.", emoji: "📅"},
    {msg: "Yaprakta sararma demir ya da magnezyum eksikliği işaretidir — yapraktan tatbik et.", emoji: "💛"},
    {msg: "Domates için potasyum, mısır için azot, buğday için fosfor öne çıkar.", emoji: "🍅"},
    {msg: "Toprak yorgunsa bir mevsim baklagil ek — fasulye, mercimek toprağa azot kazandırır.", emoji: "🌾"},
    {msg: "Kompost altın değerinde — mutfak atığını çürütüp toprağa kazandır.", emoji: "♻️"},
    {msg: "Hayvan gübresini taze kullanma, en az 6 ay olgunlaştır — kökü yakar.", emoji: "🐄"},
    {msg: "Sonbahar yaprakları toprağa kazandır — doğal organik madde, ücretsiz!", emoji: "🍂"},
    {msg: "Toprak iyi tutunmuyorsa kil az demektir — humus ekle, su tutma artsın.", emoji: "🟫"},

    // ─── 🌿 EKİM & ROTASYON ───────────────────────────────────
    {msg: "Aynı tarlaya üst üste aynı bitkiyi ekme — toprak yorulur, hastalık birikir.", emoji: "🔁"},
    {msg: "Soğan veya sarımsak ekersen yanına nane koy — zararlı böcekleri uzaklaştırır.", emoji: "🌿"},
    {msg: "Bal arıları olmadan tozlaşma yok — tarla kenarına çiçek bandı bırak, faydası büyük.", emoji: "🐝"},
    {msg: "Karadeniz'de fındık + çay, Akdeniz'de narenciye + domates en doğal seçim.", emoji: "🗺️"},
    {msg: "İç Anadolu'da buğday ve şeker pancarı kuraklığa daha dayanıklıdır.", emoji: "🌾"},
    {msg: "Domates ve fesleğen yan yana — ikisi de daha iyi büyür, lezzet artar.", emoji: "🍃"},
    {msg: "Mısır + fasulye + kabak (üç kız kardeş) yan yana — birbirini destekler.", emoji: "🌽"},
    {msg: "Tohum ekmeden önce çimlenme testi yap: 10 tohumdan kaçı çimleniyor?", emoji: "🌱"},
    {msg: "Fide dikiminde toprağı bastır ama ezme — kök hava da ister.", emoji: "👐"},

    // ─── 🌤️ HAVA & İKLİM ─────────────────────────────────────
    {msg: "Yağmur bekleniyorsa sulamayı bir gün ertele, su tasarrufu yapmış olursun.", emoji: "☔"},
    {msg: "Sıcaklık 30°C üstüne çıkarsa bitki stres altına girer — gölgelik ya da sulama düşün.", emoji: "🥵"},
    {msg: "Sabah don uyarısı varsa hassas bitkiler için tülbent ya da malçlama hayat kurtarır.", emoji: "❄️"},
    {msg: "Rüzgar sonrası ilaçlama yapma — etken madde uçar, paranı boşa harcarsın.", emoji: "💨"},
    {msg: "Dolu beklentisinde fide ve sera örtülerini güçlendir — kayıp büyük olabilir.", emoji: "🧊"},
    {msg: "Sabah çiyiyle yapraklarda mantar başlayabilir — erken saatlerde kontrole alış.", emoji: "🍄"},
    {msg: "Aşırı sıcak günlerde sera havalandırması şart — kapılar yarım açık dursun.", emoji: "🪟"},

    // ─── 🐛 HASTALIK & ZARARLI ────────────────────────────────
    {msg: "Yaprak alt yüzünde beyaz noktacıklar varsa beyaz sinek olabilir — sarı yapışkan tuzak kur.", emoji: "🪰"},
    {msg: "Külleme (mantar) çoğu sebzenin baş düşmanı — havalandırmayı arttır, sulamayı azalt.", emoji: "⚪"},
    {msg: "Salyangoz için tarla kenarına bira tuzağı kur — basit ama etkili.", emoji: "🍺"},
    {msg: "Birden fazla bitki ekersen tek tip zararlı tarlanın hepsini biçemez.", emoji: "🦗"},
    {msg: "Köstebek toprağı havalandırır ama köke zarar verirse koruma altına al.", emoji: "🐀"},

    // ─── 🌾 HASAT & SAKLAMA ───────────────────────────────────
    {msg: "Domatesi sap kısmı yarı yeşilken topla — sonra olgunlaşır, daha lezzetli.", emoji: "🍅"},
    {msg: "Buğdayı tane sertleşmeden hasat etme; saman tadı verir.", emoji: "🌾"},
    {msg: "Patates hasadı sonrası 2 hafta serin yerde dinlendir — kabuk sertleşir.", emoji: "🥔"},
    {msg: "Üzümü sabah kuru havada topla — daha uzun saklanır.", emoji: "🍇"},
    {msg: "Soğan ve sarımsak hasat sonrası 1 hafta gölgede kurutulmalı.", emoji: "🧄"},
    {msg: "Tohum saklamak için cam kavanoz kullan, kuru ve serin yerde tut.", emoji: "🥚"},

    // ─── ⚙️ SENSÖR & PRATİK ──────────────────────────────────
    {msg: "Sensörler 15-30 cm derinlikte ölçüm alır — bitki köklerinin olduğu yer.", emoji: "📏"},
    {msg: "Sensörü en kritik tarla bölgesine yerleştir — uzak köşeye değil.", emoji: "📍"},
    {msg: "Sensör verisi günlerdir gelmiyorsa pil bitmiş ya da bağlantı kopmuş olabilir.", emoji: "🔋"},
    {msg: "Toprak elektrik iletkenliği yüksekse tuzluluk var — sulama suyunu kontrol et.", emoji: "⚡"},
    {msg: "Yaz aylarında toprağı malçla — nem korunur, yabani ot azalır, sulama azalır.", emoji: "🟫"},

    // ─── 💰 EKONOMİ & PLANLAMA ────────────────────────────────
    {msg: "Hasat tahminini önceden yap — pazar fiyatı dalgalanmasında kazançlı çık.", emoji: "📈"},
    {msg: "Tarım sigortası don ve doluya karşı koruma sağlar; başvuruyu erken yap.", emoji: "🛡️"},
    {msg: "Kooperatife üye olmak girdi maliyetini düşürür ve toplu satış imkanı verir.", emoji: "🤝"},
    {msg: "Bu yıl iyi giden bitkiyi defterine yaz — gelecek yıl plana ışık tutar.", emoji: "📓"},

    // ─── 🤗 FİLİZ KARAKTER ───────────────────────────────────
    {msg: "Selam çiftçi! Bugün de toprağın bereketli olsun.", emoji: "🌾"},
    {msg: "Bana tıklamayı unutma, hep yeni bir şey biliyorum!", emoji: "✨"},
    {msg: "Sağ üstten karanlık/aydınlık temayı değiştirebilirsin, gözlerim hep takip eder.", emoji: "🌗"},
    {msg: "Ben uyumayı severim ama gece gelip beni dürtersen sinirlenirim! Uyku 00:00-05:00 arası.", emoji: "😴"},
    {msg: "Yağmuru duyduğumda yapraklarım titrer — sevimli bir tepki vermiş oluyorum 💧", emoji: "🌧️"},
    {msg: "Filizden hasada uzun bir yol var, sabırlı ol — ben de yavaş yavaş büyüyorum.", emoji: "🌱"},
];

/* Filiz overseer havuzu — gözetmen rolüne odaklı sistem-özeti ipuçları. */
const FILIZ_TIPS_OVERSEER = [
    {msg: "Bölge bazlı analytics'te çiftlik dağılımını ısı haritasıyla gör.", emoji: "🗺️"},
    {msg: "Kritik uyarılar üstte; resolved işaretledikçe arşivlenir.", emoji: "🚨"},
    {msg: "Sistemde aktif çiftlik sayısı dashboard hero alanında her dakika tazelenir.", emoji: "📊"},
    {msg: "Hava verisi tüm bölgelerden günlük çekilir; eksik bölgeyi kontrol panelinde gör.", emoji: "🌦️"},
    {msg: "PDF/Excel dışa aktarımı Raporlar sayfasında — yöneticilere haftalık özet için ideal.", emoji: "📄"},
    {msg: "Model performansını ModelPerformanceLog endpoint'inde takip et — drift erken yakalan.", emoji: "🤖"},
    {msg: "Sensör hattındaki kopukluk önce uyarılarda görünür, sonra Analytics'te düşer.", emoji: "📡"},
    {msg: "Tüm çiftliklerin koordinatları haritada; tıkla, detay açılır.", emoji: "📍"},
    {msg: "Raporlar > Karşılaştırma sekmesinde iki dönemi yan yana koy, trend net görünür.", emoji: "📈"},
    {msg: "Bölge bazlı bitki dağılımı için Analytics > Dağılımlar bölümüne göz at.", emoji: "🌾"},
    {msg: "Sulama onay akışı: farmer talep eder, gözetmen olarak gözlemleyebilirsin.", emoji: "💧"},
    {msg: "Kritik uyarı seviyesi anomali eşiği aşıldığında otomatik tetiklenir.", emoji: "⚠️"},
    {msg: "7 bölge dağılımı: pasta grafiği sana hızlı manzara verir.", emoji: "🍩"},
    {msg: "Senin görevin gözlem ve analiz — değişiklikler yöneticilere bırakılır.", emoji: "👀"},
    {msg: "Bitki sağlığı modeli sonuçlarını Analytics > Tahminler sekmesinde görebilirsin.", emoji: "🌿"},
    {msg: "Çiftlik konsolidasyonu için Analytics > Bölge Tablosu çıktısı en yararlısı.", emoji: "📋"},
];

/* Filiz admin havuzu — yönetici rolüne odaklı kullanıcı/güvenlik ipuçları. */
const FILIZ_TIPS_ADMIN = [
    {msg: "Yeni kullanıcı oluştururken rol seçimi sonra değiştirilemez, dikkat et.", emoji: "👤"},
    {msg: "Çiftliği olan kullanıcı silinemez — önce çiftlikleri devret veya temizle.", emoji: "🚫"},
    {msg: "Şifre sıfırlama log'ları audit_log'da; düzenli kontrol et.", emoji: "🔐"},
    {msg: "Admin kendini silemez — sistem korur.", emoji: "🛡️"},
    {msg: "RBAC her endpoint'te aktif; bypass denemesini izle.", emoji: "🚨"},
    {msg: "Kullanıcı listesi filtrelenebilir: rol bazında daralt.", emoji: "🔍"},
    {msg: "Bcrypt cost factor şu an 12; üretimde 14'e çıkarman tavsiye edilir.", emoji: "🔒"},
    {msg: "Yeni admin oluştururken iki kez düşün — yetkisi tamamen serbesttir.", emoji: "⚖️"},
    {msg: "Sistem sağlık endpoint'i /api/health: nabız atışı için cron'a bağla.", emoji: "💓"},
    {msg: "Veritabanı yedeği dışa aktar — alembic migration'ları kapsamalı.", emoji: "💾"},
    {msg: "JWT token süresi 24 saat; settings'de TOKEN_EXPIRE_HOURS ile değiştir.", emoji: "🎟️"},
    {msg: "Roller: farmer (sahibi), developer (teknik), overseer (read-only), admin (full).", emoji: "👥"},
    {msg: "Rate limit aşıldığında 429 döner; abuse durumunda IP banla.", emoji: "🚦"},
    {msg: "Audit log'da kim ne yaptı, ne zaman — şüpheli aktiviteyi araştır.", emoji: "📜"},
    {msg: "Bandit + ruff CI'da çalışır — pre-commit hook'la yerel taramayı da koş.", emoji: "🧰"},
    {msg: "'Demo Yükle' onboarding seçeneği yeni kullanıcılar için; admin'e yaramaz.", emoji: "🌱"},
];

/* Filiz developer havuzu — geliştirici rolüne odaklı API/debug/workflow ipuçları. */
const FILIZ_TIPS_DEVELOPER = [
    {msg: "/docs altında Swagger var; tüm endpoint'leri canlı test edebilirsin.", emoji: "📚"},
    {msg: "X-API-Key header'ı dev endpoint'leri için — credentials'tan al.", emoji: "🗝️"},
    {msg: "pytest -k 'test_X' ile filtreli koş; tüm suite'i her seferinde çalıştırma.", emoji: "🧪"},
    {msg: "alembic upgrade head ile migration'ları uygula; head'i kaçırma.", emoji: "🗃️"},
    {msg: "FastAPI Depends ile auth/db session inject — DRY için kullan.", emoji: "💉"},
    {msg: "SQLAlchemy lazy loading N+1 yaratabilir — joinedload/selectinload ekle.", emoji: "🔗"},
    {msg: "Pydantic v2'de model_dump() var, dict() değil; legacy kodu güncelle.", emoji: "📦"},
    {msg: "Frontend src/main.js vanilla — modül scope global'i window-bridge ile expose.", emoji: "🌐"},
    {msg: "vitest jsdom ile DOM mock'lar; test'i frontend/tests altında tut.", emoji: "🃏"},
    {msg: "ruff format daha hızlı, black uyumlu; pre-commit'e ekle.", emoji: "⚡"},
    {msg: "GitHub Actions CI .github/workflows altında; matrix Python 3.11/3.12.", emoji: "🤖"},
    {msg: "API_BASE_URL env'den gelir; lokal dev için .env.local kullan.", emoji: "🔧"},
    {msg: "Pre-commit hooks: trim whitespace, ruff, bandit — her commit'i denetler.", emoji: "🪝"},
    {msg: "Bug bulduğunda issue aç, branch fix/X ile çalış, PR --web ile gönder.", emoji: "🔬"},
    {msg: "Logger seviyeleri: DEBUG > INFO > WARN > ERROR — settings'de set et.", emoji: "📋"},
    {msg: "Code review öncesi self-review yap; diff'i kendin oku.", emoji: "🤝"},
];

/* Rol → havuz seçici. Anonim/bilinmeyen rol farmer'a düşer. */
function _getRoleTips(role) {
    switch (role) {
        case 'overseer':  return FILIZ_TIPS_OVERSEER;
        case 'admin':     return FILIZ_TIPS_ADMIN;
        case 'developer': return FILIZ_TIPS_DEVELOPER;
        default:          return FILIZ_TIPS_FARMER;  // farmer + anonim fallback
    }
}

/* ─── Hero subtitle dinamik Filiz tipi (Item 8a) ─────────────────────────
 * 8 farmer-anlamlı sayfada hero banner'ın altındaki `<p class="hero-filiz-tip">`
 * sayfa-açıklaması yerine rol-aware Filiz havuzundan (Item 8b _getRoleTips)
 * rastgele tip yansıtır. Sayfa
 * açılışında değişir + 20sn'de bir refresh. Yönetim sayfalarına (kullanıcılar,
 * hesabım, analytics, harita, çiftlik-detayı) dokunulmaz; orada mevcut açıklama
 * statik kalır (bu sayfalarda `<p>`'ye `.hero-filiz-tip` class'ı yok). */
const _HERO_TIP_PAGES = new Set([
    'dashboard', 'fields', 'sensors', 'weather',
    'irrigation', 'fertilizer', 'plants', 'alerts',
]);
const _HERO_TIP_REFRESH_MS = 20000;
let _heroTipInterval = null;

function _pickHeroTip() {
    // Item 8b: rol-aware — currentUser.role'a göre uygun havuzdan çek.
    // farmer-anlamlı sayfalarda admin/overseer/dev kendi havuzunu kullanır.
    const tips = _getRoleTips(currentUser?.role);
    const tip = tips[Math.floor(Math.random() * tips.length)];
    return `${tip.emoji} ${tip.msg}`;
}

function _applyHeroTip(pageId) {
    if (!_HERO_TIP_PAGES.has(pageId)) return;
    const p = document.querySelector(`p.hero-filiz-tip[data-page="${pageId}"]`);
    if (!p) return;
    // Fade out → değiştir → fade in (smooth geçiş)
    p.classList.add('fading');
    setTimeout(() => {
        p.textContent = _pickHeroTip();
        p.classList.remove('fading');
    }, 350);  // CSS transition süresiyle eşle
}

function _startHeroTipRotation(pageId) {
    // Eski interval'ı temizle (sayfa değişimi)
    if (_heroTipInterval) {
        clearInterval(_heroTipInterval);
        _heroTipInterval = null;
    }
    if (!_HERO_TIP_PAGES.has(pageId)) return;
    // İlk yansıma — fade animasyonu olmadan anında değiştir (sayfa girişinde
    // hemen Filiz tipini göster, sayfa-açıklamasını birkaç saniye okutma).
    const p = document.querySelector(`p.hero-filiz-tip[data-page="${pageId}"]`);
    if (p) p.textContent = _pickHeroTip();
    // Periyodik yenileme (fade'li)
    _heroTipInterval = setInterval(() => _applyHeroTip(pageId), _HERO_TIP_REFRESH_MS);
}

/* Filiz selamlamaları — rol + saate göre seçilir (Item 8b).
 * Anonim/bilinmeyen rol farmer'a düşer. Mood 'sleepy' (00-05) saat dilimini
 * override eder. Eski FILIZ_GREETINGS_{MORNING,NOON,EVENING,SLEEPY} ve
 * (kullanılmayan) WORRIED bu objeye taşındı. */
const FILIZ_GREETINGS = {
    farmer: {
        morning: ["Günaydın 🌅", "Erken başlayan kazanır ☀️", "İyi sabahlar 🐓", "Tarla seni bekliyor 🌱"],
        noon:    ["İyi günler 🌞", "Bereketli öğleden sonra 🌾", "Tarla nasıl bugün?", "Şu güneşe bak ☀️"],
        evening: ["İyi akşamlar 🌇", "Hava serinliyor 🌙", "Akşamın hayrına 🌒", "Bugün de bereketli geçti mi?"],
        sleepy:  ["Mhmm... 😴", "Geç oldu... zzz", "Uykum geldi 🌙", "Sen de uyu artık 🛏️"],
    },
    overseer: {
        morning: ["Günaydın gözetmen 📋", "Sistem nabzı nasıl? 📊", "İyi sabahlar 👀", "Sabahın hayrına 🌅"],
        noon:    ["İyi günler gözetmen 📋", "Sistemde sakin mi? 🔍", "Raporlar bekliyor 📈"],
        evening: ["İyi akşamlar gözetmen 🌇", "Günün özeti hazır mı? 📜", "Hayırlı akşamlar 🌙"],
        sleepy:  ["Sistem uyandığında bakalım 😴", "Mhmm... 🌙", "Geç oldu gözetmen 🛏️"],
    },
    admin: {
        morning: ["Günaydın admin 🛡️", "Sistemi açıyoruz 🔑", "İyi sabahlar yönetici 🌅"],
        noon:    ["İyi günler admin 🛡️", "Sistem güvende mi? 🔐", "Konsol seni bekliyor 💻"],
        evening: ["İyi akşamlar admin 🌇", "Günün audit raporu? 📜", "Hayırlı akşamlar 🌙"],
        sleepy:  ["Sistem boş mu? Uyu 🌙", "Mhmm... 😴", "Bile bile uyuyamazsın admin 🛏️"],
    },
    developer: {
        morning: ["Günaydın developer ⌨️", "Coffee + commits ☕", "İyi sabahlar 🌅"],
        noon:    ["İyi günler developer 💻", "Bugs found? 🐛", "Tests green? 🟢"],
        evening: ["İyi akşamlar 🌇", "Last commit zamanı 📦", "Wrap-up 🌙"],
        sleepy:  ["git commit -m 'sleeping' 😴", "Uyu, tests sabah var 🛏️", "Geç oldu... zzz"],
    },
};

function pickFilizGreetings() {
    const role = (currentUser?.role && FILIZ_GREETINGS[currentUser.role]) ? currentUser.role : 'farmer';
    const set = FILIZ_GREETINGS[role];
    if (filizMood === 'sleepy') return set.sleepy;
    const h = new Date().getHours();
    if (h >= 5 && h < 12)  return set.morning;
    if (h >= 12 && h < 18) return set.noon;
    return set.evening;  // 18-23 (00-04 mood=sleepy ile yakalanıyor)
}

let filizMood = 'happy';        // 'happy' | 'worried' | 'sleepy'
let filizCriticalAlerts = [];

function setFilizMood(mood) {
    filizMood = mood;
    const mascot = document.getElementById('filizMascot');
    if (!mascot) return;
    mascot.dataset.mood = mood;
    // Ağız değişimi
    mascot.querySelectorAll('.mouth-happy, .mouth-worried, .mouth-sleepy').forEach(el => el.style.display = 'none');
    mascot.querySelectorAll(`.mouth-${mood}`).forEach(el => el.style.display = '');
    // Z'ler ve ter damlası
    const zzz = mascot.querySelector('.filiz-zzz');
    const sweat = mascot.querySelector('.filiz-sweat');
    if (zzz) zzz.style.display = mood === 'sleepy' ? '' : 'none';
    if (sweat) sweat.style.display = mood === 'worried' ? '' : 'none';
}

function initFiliz() {
    const mascot = document.getElementById('filizMascot');
    const bubble = document.getElementById('filizBubble');
    const messageEl = document.getElementById('filizMessage');
    const tipEl = document.getElementById('filizTip');
    if (!mascot || !bubble) return;

    let bubbleVisible = false;
    let hideTimer = null;

    const showCustomMessage = (greeting, msg, tip = 'Tıklayarak başka bir ipucu al ✨', autoCloseMs = 8000) => {
        messageEl.innerHTML = `<div style="margin-bottom:6px;font-weight:500;">${greeting}</div>${msg}`;
        tipEl.textContent = tip;
        bubble.classList.add('show');
        bubbleVisible = true;
        clearTimeout(hideTimer);
        if (autoCloseMs > 0) {
            hideTimer = setTimeout(() => {
                bubble.classList.remove('show');
                bubbleVisible = false;
            }, autoCloseMs);
        }
    };

    /**
     * v6-1 (Item 8b binding): Farmer için critical alert varsa Filiz mesajına
     * yansıt — ölü kodu canlandır (`filizCriticalAlerts` zaten 60sn'de bir
     * çekiliyor ama mevcut bubble random tip gösteriyordu).
     *
     * Strateji: %50 olasılıkla critical alert mesajı, %50 normal random tip
     * (farmer'ı sürekli alertle bombalamamak için). Sleepy mood'da alert
     * görmezden gelinir — gece kullanıcıyı strese sokma.
     *
     * Sadece farmer için aktif: admin/overseer/developer kendi alert UI'larına
     * (header çanı, /api/alerts sayfası) sahip; mascot farmer'ın "sahada
     * çağırıcı sesi" rolünde.
     */
    const pickCriticalIfAny = () => {
        if (currentUser?.role !== 'farmer') return null;
        if (filizMood === 'sleepy') return null;
        if (!filizCriticalAlerts || filizCriticalAlerts.length === 0) return null;
        if (Math.random() > 0.5) return null;  // %50 — kullanıcıyı bombalamayı önle
        const alert = filizCriticalAlerts[0];  // API en yeni first dönüyor
        if (!alert || !alert.message) return null;
        return {
            greeting: 'Aa, dikkat! 😟',
            msg: `🚨 ${alert.message}`,
            tip: 'Uyarılar sayfasından detayı gör →',
        };
    };

    const pickTip = () => {
        // v6-1: Critical alert varsa öncelik tanı (farmer için, %50 olasılıkla)
        const critical = pickCriticalIfAny();
        if (critical) return critical;
        // Item 8b: rol-aware havuz + isim ile kişiselleştirme.
        const tips = _getRoleTips(currentUser?.role);
        const tip = tips[Math.floor(Math.random() * tips.length)];
        const greetingList = pickFilizGreetings();
        const baseGreeting = greetingList[Math.floor(Math.random() * greetingList.length)];
        // İlk ad ile selam kişiselleştir; sleepy mood'da uyku tonunu koru (isim ekleme).
        const firstName = currentUser?.name?.trim().split(/\s+/)[0];
        const greeting = (firstName && filizMood !== 'sleepy')
            ? `${baseGreeting} — ${firstName}`
            : baseGreeting;
        return {
            greeting,
            msg: `${tip.emoji} ${tip.msg}`,
            tip: 'Tıklayarak başka bir ipucu al ✨',
        };
    };

    const showSmart = () => {
        const t = pickTip();
        showCustomMessage(t.greeting, t.msg, t.tip);
    };

    mascot.addEventListener('click', () => {
        // Uyku zamanında tıklanırsa Filiz sinirlenir (uyandırıldı!), aksi halde sevinir
        const stateClass = filizMood === 'sleepy' ? 'angry' : 'happy';
        const duration = stateClass === 'angry' ? 1500 : 1700;
        mascot.classList.add(stateClass);
        setTimeout(() => mascot.classList.remove(stateClass), duration);
        showSmart();
    });

    // İlk selam (3 sn)
    setTimeout(() => { if (!bubbleVisible) showSmart(); }, 3000);

    // Bubble dışına tıklayınca kapat
    document.addEventListener('click', (e) => {
        if (bubbleVisible && !mascot.contains(e.target) && !bubble.contains(e.target)) {
            bubble.classList.remove('show');
            bubbleVisible = false;
            clearTimeout(hideTimer);
        }
    });

    // ─── 👀 GÖZ TAKİBİ ──────────────────────────────────────
    const pupilL = document.getElementById('filizPupilL');
    const pupilR = document.getElementById('filizPupilR');
    document.addEventListener('mousemove', (e) => {
        if (!pupilL || !pupilR) return;
        const rect = mascot.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const dx = e.clientX - cx;
        const dy = e.clientY - cy;
        const dist = Math.hypot(dx, dy);
        const max = 2.2;  // SVG koordinatlarında pupil hareket aralığı
        const ux = (dx / Math.max(dist, 1)) * Math.min(dist / 100, 1) * max;
        const uy = (dy / Math.max(dist, 1)) * Math.min(dist / 100, 1) * max;
        pupilL.style.transform = `translate(${ux}px, ${uy}px)`;
        pupilR.style.transform = `translate(${ux}px, ${uy}px)`;
    });

    // ─── 🎭 MOOD: sadece gündüz/gece — happy ↔ sleepy ─────────
    // (Worried otomatik tetiklenmez; alert mesajları konuşma balonunda gösterilir.)
    const updateMood = async () => {
        const hour = new Date().getHours();
        const isLateNight = hour < 5;
        setFilizMood(isLateNight ? 'sleepy' : 'happy');

        // Alert listesini balon için arka planda topla (mood'u etkilemez)
        if (apiOnline) {
            try {
                const alerts = await api('/api/alerts/?severity=critical&is_resolved=false&limit=10');
                filizCriticalAlerts = alerts || [];
            } catch {
                filizCriticalAlerts = [];
            }
        } else {
            filizCriticalAlerts = [];
        }
    };
    updateMood();
    setInterval(updateMood, 60000);  // 1 dk'da bir tekrar kontrol
}

init();

// ─── WINDOW BRIDGE KALDIRILDI (v9a) ───────────────────────────
// Eskiden tüm public function'lar inline `on*` handler'lar için window'a
// expose ediliyordu. v9a'da statik + dinamik tüm inline handler'lar
// `data-action` event delegation'a çevrildi (yukarıdaki actionMap +
// click/change/keydown listener'ları). Artık global window pollution yok;
// fonksiyonlar modül scope'unda closure olarak dispatcher'dan çağrılıyor.
//
// NOT: CSP `script-src 'unsafe-inline'` HÂLÂ gerekli — Swagger UI (/docs)
// inline script kullanıyor. Yani bridge kaldırma CSP'yi sıkılaştırmıyor;
// kazanım kod temizliği (no global namespace pollution).
