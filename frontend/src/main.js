/* ============================================================
   SFDAP Dashboard — Entry Point
   ============================================================
   B-batch (Cycle 9): ES module entry-point. Reusable helpers
   `src/lib/` altına ayrıldı, drift TODO kapandı.

   Bu dosya `<script type="module">` ile yüklenir. Inline `onclick`
   handler'lar `window` global'ine ihtiyaç duyar — dosyanın sonunda
   tüm public function'lar `window.X = X` ile expose edilir
   (window-bridge bölümü).
   ============================================================ */

import { _skeletonBlock, _skeletonCards, _skeletonRows, _setBusy } from "./lib/skeleton.js";
import { loadMap as _loadMapImpl } from "./lib/map.js";

const API_BASE = window.location.origin;
const AUTH_TOKEN_KEY = 'sfdap_auth_token';
let refreshInterval = null;
let charts = {};
let apiOnline = false;
// Son /me snapshot — header badge + role-aware UI guard'ları için.
// Login/logout sırasında refreshAuthState() bu objeyi güncelliyor.
let currentUser = null;

// ─── API SERVICE ──────────────────────────────────────────────

/**
 * Auth header builder — Bearer token varsa Authorization, yoksa X-API-Key.
 * REBUILD Faz 2 / Adım 7: tek noktadan auth header bind'i; rol-aware
 * endpoint'ler (`/api/dashboard/summary`, `/api/auth/me` vb) Bearer ister.
 */
function _authHeaders() {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    return token
        ? { 'Authorization': `Bearer ${token}` }
        : { 'X-API-Key': 'dev-api-key' };  // anonim fallback (eski endpoint'ler)
}

async function api(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', ..._authHeaders(), ...options.headers },
            ...options
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn(`API Error: ${endpoint}`, e);
        return null;
    }
}

/**
 * Bearer-zorunlu API çağrısı — token yoksa null + auth sayfasına yönlendirir.
 * Dashboard summary, sensors, alerts gibi RBAC'lı endpoint'ler için kullanılır.
 * 401/403 dönerse token temizler ve toast gösterir.
 */
async function apiAuth(endpoint, options = {}) {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (!token) {
        // Login formuna yumuşak yönlendirme; hard reload yok.
        if (location.hash !== '#auth') location.hash = '#auth';
        return null;
    }
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`, ...options.headers },
            ...options
        });
        if (res.status === 401) {
            // Token expire ya da revoke
            localStorage.removeItem(AUTH_TOKEN_KEY);
            currentUser = null;
            _renderUserBadge(null);
            showToast('Oturum süresi doldu, tekrar giriş yap', 'warning');
            location.hash = '#auth';
            return null;
        }
        if (res.status === 403) {
            showToast('Bu işlem için yetkin yok', 'warning');
            return null;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn(`API Auth Error: ${endpoint}`, e);
        return null;
    }
}

// ─── NAVIGATION ───────────────────────────────────────────────
const pageTitles = {
    dashboard: ['Genel Bakış', 'Tarlanın özeti'],
    fields: ['Tarlalarım', 'Çiftliklerine bağlı tarlalar'],
    'field-detail': ['Tarla Detayı', 'Sensör, sulama, hastalık ve toprak'],
    weather: ['Hava Durumu', 'Sıcaklık, nem ve yağış'],
    irrigation: ['Sulama', 'Önerilen su miktarı ve geçmiş'],
    fertilizer: ['Gübreleme', 'NPK önerisi ve takvim'],
    sensors: ['Sensörler', 'Tarladaki ölçüm cihazları'],
    analytics: ['Raporlar', 'Bölge bazında özet ve dışa aktarma'],
    map: ['Türkiye Haritası', 'Çiftliklerin coğrafi dağılımı'],
    plants: ['Bitki Sağlığı', 'Yapraktan hastalık tespiti'],
    alerts: ['Uyarılar', 'Sistem ve sensör uyarıları'],
    users: ['Kullanıcı Yönetimi', 'Tüm kullanıcılar (admin)'],
    auth: ['Hesabım', 'Profil ve şifre'],
};

function navigate(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.remove('active');
        // Drop aria-current from inactive nav items.
        n.removeAttribute('aria-current');
    });
    document.getElementById(`page-${page}`).classList.add('active');
    const navItem = document.querySelector(`[href="#${page}"]`);
    if (navItem) {
        navItem.classList.add('active');
        navItem.setAttribute('aria-current', 'page');
    }
    document.getElementById('pageTitle').textContent = pageTitles[page][0];
    document.getElementById('pageSubtitle').textContent = pageTitles[page][1];
    // Focus the <main> programmatically (tabindex=-1) so keyboard users
    // hear the page change via the screen reader.
    const main = document.getElementById('main-content');
    if (main) main.focus({ preventScroll: false });
    // Load page data
    if (page === 'dashboard') loadDashboard();
    else if (page === 'fields') loadFields();
    else if (page === 'sensors') loadSensors();
    else if (page === 'weather') loadWeather();
    else if (page === 'irrigation') loadIrrigation();
    else if (page === 'analytics') loadAnalytics();
    else if (page === 'map') loadMap();
    else if (page === 'plants') loadPlants();
    else if (page === 'alerts') loadAlerts();
    else if (page === 'users') loadUsers();
    else if (page === 'auth') refreshAuthState();
    // 'field-detail' navigate() ile değil openFieldDetail(id) ile yüklenir.
    // Close sidebar on mobile (a11y: hamburger aria-expanded sync)
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.remove('open');
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const isOpen = sidebar.classList.toggle('open');
    // Keep aria-expanded in sync with the visual sidebar state.
    const hamburger = document.querySelector('.hamburger');
    if (hamburger) hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
}

// ─── HASH ROUTER ──────────────────────────────────────────────
window.addEventListener('hashchange', () => {
    const raw = location.hash.slice(1) || 'dashboard';
    // Parametrik route: #field/{id} → tarla detayı
    if (raw.startsWith('field/')) {
        const id = parseInt(raw.split('/')[1], 10);
        if (Number.isFinite(id)) openFieldDetail(id);
        return;
    }
    if (pageTitles[raw]) navigate(raw);
});

// ─── DASHBOARD ────────────────────────────────────────────────
// REBUILD Faz 2 / Adım 8: "Çiftliğim" rol-aware kartlar
// /api/dashboard/summary tek endpoint'inden 4 metrik card + hero stats
// + trend chart'ları (Bearer-aware api() üzerinden).

const _STATUS_LABEL = { dry: 'Susuz', optimal: 'Uygun', wet: 'Aşırı sulu', no_data: 'Veri yok' };
const _STATUS_EMOJI = { dry: '🥵', optimal: '👌', wet: '💧', no_data: '—' };

function _fmtDate(iso) {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('tr-TR', { day: '2-digit', month: 'short' }); }
    catch { return iso; }
}
function _fmtNumber(v, decimals = 1) {
    if (v === null || v === undefined) return '—';
    return Number(v).toLocaleString('tr-TR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}
function _escAttr(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

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
                <button class="btn-primary" onclick="navigate('fields');toggleForm('newFarmForm')">➕ İlk çiftliğimi ekle</button>
                <button class="btn-secondary" id="loadDemoBtn" onclick="loadDemoData()">🎬 Demo verisi yükle</button>
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
                <p>⚠️ Özet alınamadı. <button class="btn-link" onclick="loadDashboard()">Tekrar dene</button></p>
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
            <button class="btn-primary" onclick="toggleForm('newFarmForm')">➕ Çiftlik Ekle</button>
            ${farms.length ? `<button class="btn-secondary" onclick="toggleForm('newFieldForm')">➕ Tarla Ekle</button>` : ''}
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
            <button class="btn-primary" onclick="submitNewFarm()">Kaydet</button>
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
            <button class="btn-primary" onclick="submitNewField()">Kaydet</button>
        </div>
    `;

    if (farms.length === 0) {
        html += `<div class="empty-state">
            <p>🌱 Henüz çiftliğin yok. Yukarıdan "Çiftlik Ekle" ile başla
               ya da <button class="btn-link" onclick="loadDemoData()">demo verisi yükle</button>.</p>
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
                    <button class="btn-mini" onclick="editFarm(${farm.id}, '${_escAttr(farm.name)}')">✏️</button>
                    <button class="btn-mini btn-danger" onclick="deleteFarm(${farm.id}, '${_escAttr(farm.name)}')">🗑</button>
                </span>
            </div>`;
        if (fields.length === 0) {
            html += '<p class="farm-no-fields">Bu çiftlikte tarla kaydı yok.</p>';
        } else {
            html += '<div class="field-cards">';
            for (const f of fields) {
                const area = f.area_hectares != null ? `${_fmtNumber(f.area_hectares)} ha` : '—';
                html += `<div class="field-card-wrap">
                    <a class="field-card" href="#field/${f.id}" onclick="openFieldDetail(${f.id});return false;">
                        <div class="field-card-name">🌱 ${_escAttr(f.name)}</div>
                        <div class="field-card-meta">${_escAttr(f.soil_type || 'toprak —')} · ${area}</div>
                        <div class="field-card-cta">Detayı gör →</div>
                    </a>
                    <button class="btn-mini btn-danger field-card-del" onclick="deleteField(${f.id}, '${_escAttr(f.name)}')" title="Tarlayı sil">🗑</button>
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

function renderFieldDetail(d) {
    const cropName = d.crop ? d.crop.name : 'Ekili bitki yok';
    const moistVal = d.avg_moisture_percent != null ? `%${_fmtNumber(d.avg_moisture_percent)}` : '—';
    const ms = d.moisture_status || 'no_data';

    // Sensör kartları
    const sensorRows = (d.sensors || []).map(s => {
        const m = s.latest_moisture_percent != null ? `%${_fmtNumber(s.latest_moisture_percent)}` : '—';
        const t = s.latest_soil_temperature_c != null ? `${_fmtNumber(s.latest_soil_temperature_c)}°C` : '—';
        return `<div class="detail-mini-card">
            <div class="detail-mini-title">📡 ${_escAttr(s.sensor_type)} <span class="sensor-status sensor-${_escAttr(s.status)}">${_escAttr(s.status)}</span></div>
            <div class="detail-mini-row">Nem: <strong>${m}</strong> · Toprak: <strong>${t}</strong></div>
            <div class="detail-mini-sub">${s.latest_reading_at ? _fmtDate(s.latest_reading_at) : 'okuma yok'}</div>
        </div>`;
    }).join('') || '<p class="detail-empty">Bu tarlada sensör yok.</p>';

    // Sulama geçmişi — pending kayıtlarda tamamla/iptal butonları
    const irrRows = (d.recent_irrigations || []).map(i => {
        const amt = i.water_amount_liters != null ? `${_fmtNumber(i.water_amount_liters, 0)} L` : '—';
        const actions = i.status === 'pending'
            ? `<button class="btn-mini" onclick="updateIrrigationStatus(${i.id}, 'completed')">✓ Tamamlandı</button>
               <button class="btn-mini btn-danger" onclick="updateIrrigationStatus(${i.id}, 'cancelled')">✗ İptal</button>`
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
                <button class="btn-mini" onclick="editField(${d.id}, '${_escAttr(d.name)}')">✏️ Düzenle</button>
                <button class="btn-mini btn-danger" onclick="deleteField(${d.id}, '${_escAttr(d.name)}')">🗑 Sil</button>
            </div>
        </div>

        <div class="cards-grid">
            <div class="metric-card metric-status-${ms}">
                <div class="metric-head"><span class="metric-icon" aria-hidden="true">💧</span><span class="metric-title">Toprak nemi (son 24 sa.)</span></div>
                <div class="metric-value">${moistVal}</div>
                <div class="metric-status"><span class="metric-status-pill">${_STATUS_EMOJI[ms]} ${_STATUS_LABEL[ms]}</span></div>
            </div>
        </div>

        <div class="section-header">📡 Sensörler</div>
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
            <button class="btn-primary" id="fieldLeafBtn" onclick="analyzeFieldLeaf()">🔬 Hastalığı Tespit Et</button>
            <div id="fieldLeafResult" style="display:none;margin-top:16px;"></div>
        </div>

        <div class="section-header">🚿 Sulama Geçmişi
            <button class="btn-mini" style="float:right;" onclick="addFieldIrrigation(${d.id})">➕ Sulama programı ekle</button>
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

function renderMoistureChart(data) {
    const sorted = [...data].reverse();
    const labels = sorted.map(d => new Date(d.recorded_at).toLocaleDateString('tr'));
    const values = sorted.map(d => d.humidity_percent);
    if (charts.moisture) charts.moisture.destroy();
    charts.moisture = new Chart(document.getElementById('moistureChart'), {
        type: 'line', data: { labels, datasets: [{ label: 'Nem %', data: values, borderColor: '#3b82f6',
            backgroundColor: 'rgba(59,130,246,.1)', fill: true, tension: .4, pointRadius: 2 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
}

function renderTempHumChart(data) {
    const sorted = [...data].reverse();
    const labels = sorted.map(d => new Date(d.recorded_at).toLocaleDateString('tr'));
    if (charts.tempHum) charts.tempHum.destroy();
    charts.tempHum = new Chart(document.getElementById('tempHumChart'), {
        type: 'line', data: { labels, datasets: [
            { label: 'Sıcaklık °C', data: sorted.map(d => d.temperature_c), borderColor: '#f59e0b', tension: .4, pointRadius: 2, yAxisID: 'y' },
            { label: 'Nem %', data: sorted.map(d => d.humidity_percent), borderColor: '#3b82f6', tension: .4, pointRadius: 2, yAxisID: 'y1' },
        ] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: {
                x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } },
                y: { position: 'left', ticks: { color: '#f59e0b' }, grid: { color: '#1f2937' } },
                y1: { position: 'right', ticks: { color: '#3b82f6' }, grid: { display: false } },
            } }
    });
}

function renderPrecipChart(data) {
    const sorted = [...data].reverse();
    const labels = sorted.map(d => new Date(d.recorded_at).toLocaleDateString('tr'));
    if (charts.precip) charts.precip.destroy();
    charts.precip = new Chart(document.getElementById('precipChart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Yağış mm', data: sorted.map(d => d.precipitation_mm),
            backgroundColor: 'rgba(6,182,212,.5)', borderColor: '#06b6d4', borderWidth: 1 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
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
            style="cursor:pointer" onclick="loadSensorDetail(${s.id})"
            onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();loadSensorDetail(${s.id});}">
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
                   <button class="btn-primary" onclick="approveIrrigation()">✅ Onayla ve programa ekle</button>
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
const analyticsColors = {
    green: '#10b981', blue: '#3b82f6', amber: '#f59e0b',
    red: '#ef4444', violet: '#8b5cf6', cyan: '#06b6d4',
    pink: '#ec4899', lime: '#84cc16',
};

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

function renderSensorTypeChart(dist) {
    const typeLabels = { 'soil_moisture': 'Toprak Nemi', 'soil_temperature': 'Toprak Sıcaklığı', 'electrical_conductivity': 'Elektriksel İletkenlik' };
    const colors = [analyticsColors.green, analyticsColors.amber, analyticsColors.cyan, analyticsColors.violet, analyticsColors.pink];
    if (charts.sensorType) charts.sensorType.destroy();
    charts.sensorType = new Chart(document.getElementById('sensorTypeChart'), {
        type: 'doughnut',
        data: {
            labels: dist.map(d => typeLabels[d.type] || d.type),
            datasets: [{ data: dist.map(d => d.count), backgroundColor: colors.slice(0, dist.length), borderColor: 'transparent', borderWidth: 0 }]
        },
        options: {
            responsive: true, cutout: '60%',
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 16, font: { size: 12 } } } }
        }
    });
}

function renderFarmTempChart(comparison) {
    if (!comparison.length) return;
    // Bölge bazlı gruplama (il → 7 coğrafi bölge)
    const regionMap = {};
    comparison.forEach(f => {
        const region = f.region || 'Diğer';
        if (!regionMap[region]) regionMap[region] = { temps: [], hums: [], precips: [], count: 0 };
        regionMap[region].temps.push(f.temperature.avg);
        regionMap[region].hums.push(f.humidity?.avg || 0);
        regionMap[region].count++;
    });
    const regions = Object.keys(regionMap);
    const avgByRegion = regions.map(r => {
        const t = regionMap[r].temps;
        return { region: r, avg: +(t.reduce((a,b) => a+b, 0) / t.length).toFixed(1),
            min: +Math.min(...t).toFixed(1), max: +Math.max(...t).toFixed(1), count: regionMap[r].count };
    });
    avgByRegion.sort((a, b) => b.avg - a.avg);
    const labels = avgByRegion.map(r => `${r.region} (${r.count})`);
    if (charts.farmTemp) charts.farmTemp.destroy();
    charts.farmTemp = new Chart(document.getElementById('farmTempChart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Min °C', data: avgByRegion.map(r => r.min), backgroundColor: analyticsColors.blue + '99' },
                { label: 'Ort °C', data: avgByRegion.map(r => r.avg), backgroundColor: analyticsColors.amber + '99' },
                { label: 'Max °C', data: avgByRegion.map(r => r.max), backgroundColor: analyticsColors.red + '99' },
            ]
        },
        options: {
            responsive: true, indexAxis: 'y',
            plugins: { legend: { labels: { color: '#9ca3af' } },
                title: { display: true, text: 'Bölge Bazlı Sıcaklık Karşılaştırması', color: '#9ca3af', font: { size: 13 } } },
            scales: {
                x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' }, title: { display: true, text: '°C', color: '#6b7280' } },
                y: { ticks: { color: '#9ca3af', font: { size: 11 } }, grid: { color: '#1f2937' } }
            }
        }
    });
}

function renderIrrigationStatusChart(dist) {
    const statusLabels = { 'completed': 'Tamamlandı', 'pending': 'Bekliyor', 'cancelled': 'İptal Edildi' };
    const statusColors = { 'completed': analyticsColors.green, 'pending': analyticsColors.amber, 'cancelled': analyticsColors.red };
    if (charts.irrigationStatus) charts.irrigationStatus.destroy();
    charts.irrigationStatus = new Chart(document.getElementById('irrigationStatusChart'), {
        type: 'polarArea',
        data: {
            labels: dist.map(d => statusLabels[d.status] || d.status),
            datasets: [{
                data: dist.map(d => d.count),
                backgroundColor: dist.map(d => (statusColors[d.status] || analyticsColors.violet) + '80'),
                borderColor: dist.map(d => statusColors[d.status] || analyticsColors.violet),
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 16, font: { size: 12 } } } },
            scales: { r: { ticks: { color: '#6b7280', backdropColor: 'transparent' }, grid: { color: '#1f293766' } } }
        }
    });
}

function renderNpkRadarChart(profiles) {
    const colors = [analyticsColors.green, analyticsColors.blue, analyticsColors.red];
    if (charts.npkRadar) charts.npkRadar.destroy();
    charts.npkRadar = new Chart(document.getElementById('npkRadarChart'), {
        type: 'radar',
        data: {
            labels: profiles.map(p => p.crop),
            datasets: [
                { label: 'Azot (N)', data: profiles.map(p => p.N), borderColor: analyticsColors.green, backgroundColor: analyticsColors.green + '20', pointBackgroundColor: analyticsColors.green, pointRadius: 3 },
                { label: 'Fosfor (P)', data: profiles.map(p => p.P), borderColor: analyticsColors.blue, backgroundColor: analyticsColors.blue + '20', pointBackgroundColor: analyticsColors.blue, pointRadius: 3 },
                { label: 'Potasyum (K)', data: profiles.map(p => p.K), borderColor: analyticsColors.amber, backgroundColor: analyticsColors.amber + '20', pointBackgroundColor: analyticsColors.amber, pointRadius: 3 },
            ]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 16 } } },
            scales: { r: { ticks: { color: '#6b7280', backdropColor: 'transparent' }, grid: { color: '#1f293766' }, pointLabels: { color: '#9ca3af', font: { size: 11 } } } }
        }
    });
}

function renderDailyTrendChart(trends) {
    if (!trends.length) return;
    // Bölge bazlı gruplama: Her bölge için ortalama günlük sıcaklık
    const regionTrends = {};
    trends.forEach(farm => {
        const region = farm.region || 'Diğer';
        if (!regionTrends[region]) regionTrends[region] = { days: {} };
        farm.days.forEach(d => {
            if (!regionTrends[region].days[d.date]) regionTrends[region].days[d.date] = { temps: [], hums: [] };
            if (d.temp_avg != null) regionTrends[region].days[d.date].temps.push(d.temp_avg);
        });
    });
    const regionColors = [
        analyticsColors.red, analyticsColors.blue, analyticsColors.green,
        analyticsColors.violet, analyticsColors.amber, analyticsColors.cyan, analyticsColors.pink
    ];
    const regionNames = Object.keys(regionTrends);
    // İlk bölgenin tarihlerini al
    const allDates = Object.keys(regionTrends[regionNames[0]]?.days || {}).sort();
    const datasets = regionNames.map((region, i) => {
        const data = allDates.map(date => {
            const day = regionTrends[region].days[date];
            if (!day || !day.temps.length) return null;
            return +(day.temps.reduce((a,b) => a+b, 0) / day.temps.length).toFixed(1);
        });
        return {
            label: region, data,
            borderColor: regionColors[i % regionColors.length],
            backgroundColor: regionColors[i % regionColors.length] + '15',
            fill: false, tension: 0.4, pointRadius: 3, borderWidth: 2,
        };
    });
    const labels = allDates.map(d => d.slice(5));
    if (charts.dailyTrend) charts.dailyTrend.destroy();
    charts.dailyTrend = new Chart(document.getElementById('dailyTrendChart'), {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#9ca3af', font: { size: 11 } } },
                title: { display: true, text: 'Bölge Bazlı Günlük Sıcaklık Trendi', color: '#9ca3af', font: { size: 13 } } },
            scales: {
                x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } },
                y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' }, title: { display: true, text: '°C', color: '#6b7280' } }
            }
        }
    });
}

function renderSensorStatsChart(stats) {
    if (!stats || !stats.moisture.avg) return;
    if (charts.sensorStats) charts.sensorStats.destroy();
    charts.sensorStats = new Chart(document.getElementById('sensorStatsChart'), {
        type: 'bar',
        data: {
            labels: ['Toprak Nemi (%)', 'Toprak Sıcaklığı (°C)'],
            datasets: [
                { label: 'Min', data: [stats.moisture.min, stats.soil_temperature.min], backgroundColor: analyticsColors.blue + '80' },
                { label: 'Ortalama', data: [stats.moisture.avg, stats.soil_temperature.avg], backgroundColor: analyticsColors.green + '80' },
                { label: 'Max', data: [stats.moisture.max, stats.soil_temperature.max], backgroundColor: analyticsColors.red + '80' },
            ]
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: {
                x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } },
                y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }
            }
        }
    });
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
            : `<button class="btn-secondary" style="padding:4px 10px;" onclick="resolveAlert(${a.id})" aria-label="Uyarıyı çözüldü olarak işaretle">Çöz</button>`;
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
// `AUTH_TOKEN_KEY` constant'ı dosyanın başında tanımlı (top-level state ile birlikte).

function getAuthToken() { return localStorage.getItem(AUTH_TOKEN_KEY); }
function setAuthToken(t) { localStorage.setItem(AUTH_TOKEN_KEY, t); }
function clearAuthToken() { localStorage.removeItem(AUTH_TOKEN_KEY); }

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
    const landing = document.getElementById('landing');
    const app = document.querySelector('.app');
    if (!landing || !app) return;
    if (user) {
        landing.style.display = 'none';
        app.style.display = '';  // flex (CSS default)
    } else {
        landing.style.display = 'flex';
        app.style.display = 'none';
    }
}

/**
 * Rol-aware nav görünürlüğü — `[data-role]` taşıyan nav item'ları yalnız
 * eşleşen role gösterir (örn. admin "Kullanıcılar"). user null ise hepsi gizli.
 */
function _applyRoleVisibility(user) {
    document.querySelectorAll('[data-role]').forEach(el => {
        const need = el.getAttribute('data-role');
        el.style.display = (user && user.role === need) ? '' : 'none';
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
                        <button class="btn-mini" onclick="resolveFromBell(${a.id})">Çöz</button>
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

async function doLogin() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    if (!email || !password) { showToast('E-posta ve şifre gerekli', 'warning'); return; }
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
    if (!name || !email || !password) { showToast('Tüm alanlar gerekli', 'warning'); return; }
    if (password.length < 8) { showToast('Şifre en az 8 karakter olmalı', 'warning'); return; }
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
            <td><select class="user-role-select" onchange="changeUserRole(${u.id}, this.value)">${roleOpts(u.role)}</select></td>
            <td>${u.owned_farms_count ?? 0}</td>
            <td>${_fmtDate(u.created_at)}</td>
            <td class="user-actions">
                <button class="btn-mini" onclick="resetUserPassword(${u.id}, '${_escAttr(u.email)}')">🔑 Şifre</button>
                <button class="btn-mini btn-danger" onclick="deleteUser(${u.id}, '${_escAttr(u.email)}')">🗑 Sil</button>
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

// ─── STATUS & UTILITIES ───────────────────────────────────────
function updateStatus(online) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    dot.className = `status-dot ${online ? 'online' : 'offline'}`;
    text.textContent = online ? 'Sistem Aktif' : 'Bağlantı Yok';
}

function showToast(message, type = 'info', duration = 3500) {
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

function updateClock() {
    document.getElementById('clockDisplay').textContent = new Date().toLocaleTimeString('tr');
}

// ─── INIT ─────────────────────────────────────────────────────
async function init() {
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
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    // İlk tema: localStorage > sistem tercihi > dark default
    const stored = localStorage.getItem(STORAGE_KEY);
    const prefersLight = window.matchMedia?.('(prefers-color-scheme: light)').matches;
    const initial = stored || (prefersLight ? 'light' : 'dark');
    applyTheme(initial);

    btn.addEventListener('click', () => {
        const current = root.dataset.theme || 'dark';
        const next = current === 'light' ? 'dark' : 'light';
        applyTheme(next);
        localStorage.setItem(STORAGE_KEY, next);
        // Sayfa yeniden yüklenmiyor — toast bildirimi çıkmasın diye.
        // Chart.js renkleri mevcut sayfada eski temada kalır; sayfa değişince güncellenir.
    });

    function applyTheme(theme) {
        if (theme === 'light') {
            root.dataset.theme = 'light';
            btn.setAttribute('aria-label', 'Karanlık temaya geç');
            btn.setAttribute('title', 'Karanlık temaya geç');
        } else {
            delete root.dataset.theme;
            btn.setAttribute('aria-label', 'Aydınlık temaya geç');
            btn.setAttribute('title', 'Aydınlık temaya geç');
        }
    }
}

/* ─── 🌱 FİLİZ MASKOTU ─────────────────────────────────────── */

// Filiz'in tüm tarımsal ipuçları — tek havuz, sayfaya bağımsız
const FILIZ_TIPS = [
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

/* Filiz selamlamaları — saat dilimine göre seçilir (sevimlilik pack) */
const FILIZ_GREETINGS_MORNING = ["Günaydın çiftçi! 🌅", "Erken başlayan kazanır ☀️", "İyi sabahlar 🐓", "Tarla seni bekliyor 🌱"];
const FILIZ_GREETINGS_NOON    = ["İyi günler! 🌞", "Bereketli öğleden sonra 🌾", "Tarla nasıl bugün?", "Şu güneşe bak ☀️"];
const FILIZ_GREETINGS_EVENING = ["İyi akşamlar 🌇", "Hava serinliyor 🌙", "Akşamın hayrına 🌒", "Bugün de bereketli geçti mi? 🌾"];
const FILIZ_GREETINGS_WORRIED = ["Aaa, bir şey var 😟", "Dikkat! ⚠️", "Olamaz!", "Acele etmen lazım..."];
const FILIZ_GREETINGS_SLEEPY  = ["Mhmm... 😴", "Geç oldu... zzz", "Uykum geldi 🌙", "Sen de uyu artık 🛏️"];

function pickFilizGreetings() {
    if (filizMood === 'sleepy') return FILIZ_GREETINGS_SLEEPY;
    const h = new Date().getHours();
    if (h >= 5 && h < 12)  return FILIZ_GREETINGS_MORNING;
    if (h >= 12 && h < 18) return FILIZ_GREETINGS_NOON;
    return FILIZ_GREETINGS_EVENING;   // 18-23 (00-04 mood=sleepy ile yakalanıyor)
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

    const pickTip = () => {
        // Tek havuzdan rastgele tarımsal ipucu
        const tip = FILIZ_TIPS[Math.floor(Math.random() * FILIZ_TIPS.length)];
        const greetingList = pickFilizGreetings();
        const greeting = greetingList[Math.floor(Math.random() * greetingList.length)];
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

// ─── WINDOW BRIDGE ────────────────────────────────────────────
// `<script type="module">` module scope'ta function decls global olmuyor.
// `index.html`'deki 12 inline `on*` handler (navigate, toggleSidebar,
// loadSensors, loadIrrigation, predictIrrigation, recommendFertilizer,
// fertilizerSchedule, analyzePlantImage, loadAlerts, doLogin,
// doRegister, doLogout) için bunları window'a expose etmek gerekiyor.
//
// Bu köprü Cycle 9 sonrası event delegation'a çevrilerek kaldırılabilir;
// o zaman CSP `script-src 'unsafe-inline'`'ı drop edilir.
Object.assign(window, {
    navigate,
    toggleSidebar,
    loadSensors,
    loadIrrigation,
    predictIrrigation,
    recommendFertilizer,
    fertilizerSchedule,
    analyzePlantImage,
    loadAlerts,
    loadDashboard,
    loadDemoData,
    loadFields,
    openFieldDetail,
    analyzeFieldLeaf,
    toggleForm,
    submitNewFarm,
    submitNewField,
    editFarm,
    deleteFarm,
    editField,
    deleteField,
    approveIrrigation,
    updateIrrigationStatus,
    addFieldIrrigation,
    toggleBell,
    runAlertCheck,
    resolveFromBell,
    loadUsers,
    createUser,
    changeUserRole,
    resetUserPassword,
    deleteUser,
    doLogin,
    doRegister,
    doLogout,
    doChangePassword,
    toggleLandingForm,
    // Status panel ve alerts bridge için (showToast başka modüllerden çağrılıyor)
    showToast,
    resolveAlert,
    loadSensorDetail,
});
