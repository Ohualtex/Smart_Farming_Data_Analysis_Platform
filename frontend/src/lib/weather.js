import { api } from "./api.js";
import { _skeletonCards, _setBusy } from "./skeleton.js";

let weatherTempChart = null;
let weatherWindChart = null;

// ─── WEATHER ──────────────────────────────────────────────────
export async function loadWeather() {
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
    if (weatherTempChart) weatherTempChart.destroy();
    weatherTempChart = new Chart(document.getElementById('weatherTempChart'), {
        type: 'line', data: { labels, datasets: [{ label: 'Sıcaklık °C', data: sorted.map(d => d.temperature_c),
            borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.1)', fill: true, tension: .4, pointRadius: 2 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
    // Wind chart
    if (weatherWindChart) weatherWindChart.destroy();
    weatherWindChart = new Chart(document.getElementById('weatherWindChart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Rüzgar km/h', data: sorted.map(d => d.wind_speed_kmh || 0),
            backgroundColor: 'rgba(139,92,246,.4)', borderColor: '#8b5cf6', borderWidth: 1 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: { x: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } }, y: { ticks: { color: '#6b7280' }, grid: { color: '#1f2937' } } } }
    });
}
