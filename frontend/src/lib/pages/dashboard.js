/* ============================================================
   SFDAP — Dashboard Page Module
   ============================================================
   Genel Bakış sayfası: rol-aware özet kartları, hero stats,
   trend chart'ları + onboarding banner + demo veri kurulumu.
   Ayrıca hero ipucu rotasyonu ve sayı-sayma animasyonu burada.
   ============================================================ */

import { _fmtDate, _fmtNumber, _escAttr, showToast, updateStatus, _STATUS_EMOJI, _STATUS_LABEL } from "../utils.js";
import { api, apiAuth, getAuthToken } from "../api.js";
import { _skeletonCards, _setBusy } from "../skeleton.js";
import { renderMoistureChart, renderTempHumChart, renderPrecipChart } from "../charts.js";
import { getCurrentUser, getApiOnline, setApiOnline } from "../session.js";
import { _getRoleTips } from "../filiz.js";
import { refreshAuthState } from "./account.js";

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
export async function loadDemoData() {
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

export async function loadDashboard() {
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
        updateStatus(getApiOnline());
        return;
    }

    const [summary, weather] = await Promise.all([
        apiAuth('/api/dashboard/summary'),
        api('/api/weather/?limit=30'),
    ]);
    setApiOnline(summary !== null);
    updateStatus(getApiOnline());

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
export function animateHeroStats() {
    ['heroFarms', 'heroSensors', 'heroReadings'].forEach(id => {
        const el = document.getElementById(id);
        if (el) animateCount(el);
    });
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
    const tips = _getRoleTips(getCurrentUser()?.role);
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

export function _startHeroTipRotation(pageId) {
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
