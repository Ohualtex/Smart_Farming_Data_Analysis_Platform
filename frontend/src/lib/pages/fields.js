/* ============================================================
   SFDAP — Fields Page Module
   ============================================================
   Tarlalarım listesi (çiftlik bazlı), Çiftlik/Tarla/Sensör CRUD
   ve Tarla Detayı sayfası. currentFieldId state'i burada tutulur
   (monitoring.js getCurrentFieldId ile okur).
   ============================================================ */

import { _fmtNumber, _escAttr, showToast } from "../utils.js";
import { apiAuth, getAuthToken, API_BASE } from "../api.js";
import { _skeletonBlock, _setBusy } from "../skeleton.js";
import { diagnosisLabel, severityLabel } from "../labels.js";
import { charts, chartTick, chartLegend, chartGrid } from "../charts.js";
import { renderFieldDetail } from "../render.js";
import { pageTitles } from "../router.js";
import { navigate } from "../nav.js";

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
    if (res) { ['nfName', 'nfCity', 'nfRegion', 'nfArea'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; }); showToast('Çiftlik eklendi ✅', 'success'); loadFields(); }
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
    if (res) { ['ndName', 'ndSoil', 'ndArea'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; }); showToast('Tarla eklendi ✅', 'success'); loadFields(); }
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
            if (currentFieldId === fieldId) { location.hash = '#fields'; navigate('fields'); }
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
        ['nsSerial', 'nsDepth'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
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

/** monitoring.js (irrigation) currentFieldId'yi okumak için kullanır. */
export function getCurrentFieldId() { return currentFieldId; }

export function openFieldDetail(fieldId) {
    currentFieldId = fieldId;
    // Sayfayı aktive et (navigate yerine doğrudan — parametrik route).
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => { n.classList.remove('active'); n.removeAttribute('aria-current'); });
    document.getElementById('page-field-detail').classList.add('active');
    document.getElementById('pageTitle').textContent = pageTitles['field-detail'][0];
    document.getElementById('pageSubtitle').textContent = pageTitles['field-detail'][1];
    if (location.hash !== `#field/${fieldId}`) location.hash = `#field/${fieldId}`;
    // navigate() ile tutarlı: sayfa tepeden açılsın, odak kaydırmasın, mobil sidebar kapansın.
    window.scrollTo(0, 0);
    const main = document.getElementById('main-content');
    if (main) main.focus({ preventScroll: true });
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.remove('open');
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
    loadFieldDetail(fieldId);
}

export async function loadFieldDetail(fieldId) {
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
        options: { responsive: true, plugins: { legend: { labels: { color: chartLegend() } } },
            scales: { x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } }, y: { ticks: { color: chartTick() }, grid: { color: chartGrid() } } } }
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
        const sevColor = sev === 'high' ? '#ef4444' : sev === 'medium' ? '#f97316' : sev === 'low' ? '#eab308' : '#22c55e';
        const box = document.getElementById('fieldLeafResult');
        box.innerHTML = `<div style="border-left:4px solid ${sevColor};padding-left:12px;">
            <h4 style="margin:0 0 6px;">🧪 ${_escAttr(diagnosisLabel(data.diagnosis))}</h4>
            <p style="margin:2px 0;">Güven: <strong>${data.confidence_score != null ? '%' + _fmtNumber(data.confidence_score * 100, 0) : '—'}</strong> · Şiddet: <strong style="color:${sevColor};">${_escAttr(severityLabel(sev))}</strong></p>
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
