import { api, apiAuth, getAuthToken } from "./api.js";
import { _skeletonCards } from "./skeleton.js";
import { fmtDate, fmtNumber, escAttr } from "./ui_helpers.js";
import { registerActions } from "./events.js";

const _STATUS_LABEL = { dry: 'Susuz', optimal: 'Uygun', wet: 'Aşırı sulu', no_data: 'Veri yok' };
const _STATUS_EMOJI = { dry: '🥵', optimal: '👌', wet: '💧', no_data: '—' };

const charts = {};

export function _renderSummaryCards(summary) {
    const moist = summary.soil_moisture_today || {};
    const irr = summary.last_irrigation || {};
    const alerts = summary.open_alerts || { by_severity: {} };
    const disease = summary.last_disease || {};
    const scopeNote = summary.scope === 'system' ? 'Sistem geneli' : 'Senin tarlalarından';

    const moistValue = moist.avg_moisture_percent != null
        ? `%${fmtNumber(moist.avg_moisture_percent)}`
        : '—';
    const moistStatus = moist.status || 'no_data';
    const irrAmount = irr.water_amount_liters != null
        ? `${fmtNumber(irr.water_amount_liters, 0)} L`
        : '—';
    const irrTitle = irr.field_name ? `${irr.field_name} · ${fmtDate(irr.scheduled_date)}` : 'Sulama kaydı yok';
    const sev = alerts.by_severity || {};
    const severityChips = [
        { key: 'critical', label: 'kritik', cls: 'critical' },
        { key: 'medium', label: 'orta', cls: 'medium' },
        { key: 'low', label: 'düşük', cls: 'low' },
    ].map(({ key, label, cls }) => {
        const cnt = sev[key] || 0;
        return cnt > 0 ? `<span class="severity-chip severity-${cls}">${cnt} ${label}</span>` : '';
    }).join(' ');

    const diseaseDx = disease.diagnosis || '—';
    const diseaseDetail = disease.diagnosis
        ? `${disease.field_name || 'Tarla'} · ${fmtDate(disease.captured_at)} · güven %${fmtNumber((disease.confidence_score || 0) * 100, 0)}`
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
            <div class="metric-context"><strong>${escAttr(irr.field_name || '—')}</strong> · ${fmtDate(irr.scheduled_date)}</div>
            <div class="metric-context">${escAttr(irr.status || (irr.irrigation_id ? '—' : 'Sulama kaydı yok'))}</div>
            <div class="metric-scope">${scopeNote}</div>
        </div>

        <div class="metric-card metric-alerts ${alerts.total > 0 ? 'has-alerts' : ''}">
            <div class="metric-head">
                <span class="metric-icon" aria-hidden="true">🚨</span>
                <span class="metric-title">Açık uyarılar</span>
            </div>
            <div class="metric-value">${alerts.total || 0}</div>
            <div class="metric-context metric-severities">${severityChips || '<span class="metric-status-pill">Açık uyarı yok ✅</span>'}</div>
            <div class="metric-context metric-latest">${alerts.latest_message ? escAttr(alerts.latest_message) : ''}</div>
            <div class="metric-scope">${scopeNote}</div>
        </div>

        <div class="metric-card metric-disease metric-severity-${disease.severity || 'none'}">
            <div class="metric-head">
                <span class="metric-icon" aria-hidden="true">🦠</span>
                <span class="metric-title">Son hastalık tanısı</span>
            </div>
            <div class="metric-value metric-value-text">${escAttr(diseaseDx)}</div>
            <div class="metric-context">${escAttr(diseaseDetail)}</div>
            <div class="metric-scope">${scopeNote}</div>
        </div>
    `;
}

export function _onboardingBannerHtml() {
    return `
        <div class="onboarding-banner" style="grid-column: 1 / -1;">
            <div class="onboarding-emoji" aria-hidden="true">🌱</div>
            <h3>Hoş geldin! Hadi başlayalım.</h3>
            <p>Henüz çiftliğin yok. İlk çiftliğini ekleyerek başlayabilir ya da
               tek tıkla örnek verilerle platformu hemen keşfedebilirsin.</p>
            <div class="onboarding-actions">
                <button class="btn-primary" data-action="dashboardNewFarm">➕ İlk çiftliğimi ekle</button>
                <button class="btn-secondary" id="loadDemoBtn" data-action="loadDemoData">🎬 Demo verisi yükle</button>
            </div>
        </div>`;
}

export async function loadDemoData() {
    const btn = document.getElementById('loadDemoBtn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Kuruluyor...'; }
    const res = await apiAuth('/api/onboarding/demo', { method: 'POST' });
    if (res) {
        window.dispatchEvent(new CustomEvent('toast', { detail: { msg: 'Demo verisi kuruldu ✅ — keşfetmeye başla!', type: 'success' } }));
        // Refresh auth state which updates header badge
        window.dispatchEvent(new CustomEvent('auth-refresh-needed'));
        loadDashboard();
    } else if (btn) {
        btn.disabled = false; btn.textContent = '🎬 Demo verisi yükle';
    }
}

export async function loadDashboard() {
    const cards = document.getElementById('dashboardCards');
    if (!cards) return;
    cards.innerHTML = _skeletonCards(4);

    const token = getAuthToken();
    if (!token) {
        cards.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <p>🔐 "Çiftliğim" özetini görmek için <a href="#auth">giriş yap</a>.</p>
            </div>
        `;
        window.dispatchEvent(new CustomEvent('status-update', { detail: { online: false } }));
        return;
    }

    const [summary, weather] = await Promise.all([
        apiAuth('/api/dashboard/summary'),
        api('/api/weather/?limit=30'),
    ]);

    const isOnline = summary !== null;
    window.dispatchEvent(new CustomEvent('status-update', { detail: { online: isOnline } }));

    if (summary && summary.scope === 'user' && summary.farm_count === 0) {
        cards.innerHTML = _onboardingBannerHtml();
        const heroFarms = document.getElementById('heroFarms');
        if (heroFarms) heroFarms.textContent = '0';
    } else if (summary) {
        cards.innerHTML = _renderSummaryCards(summary);
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

    const w = weather || [];
    renderMoistureChart(w);
    renderTempHumChart(w);
    renderPrecipChart(w);
}

export function renderMoistureChart(data) {
    if (!document.getElementById('moistureChart')) return;
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

export function renderTempHumChart(data) {
    if (!document.getElementById('tempHumChart')) return;
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

export function renderPrecipChart(data) {
    if (!document.getElementById('precipChart')) return;
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

// Register event delegation handlers
registerActions({
    'dashboardNewFarm': () => {
        window.dispatchEvent(new CustomEvent('navigate', { detail: 'fields' }));
        window.dispatchEvent(new CustomEvent('toggle-form', { detail: 'newFarmForm' }));
    },
    'loadDemoData': () => loadDemoData(),
    'loadDashboard': () => loadDashboard(),
});
