import { api } from "./api.js";
import { _skeletonRows, _setBusy } from "./skeleton.js";

let sensorDetailChart = null;

// ─── SENSORS ──────────────────────────────────────────────────
// Pagination: sayfa basi 50 kayit, slider ile sayfalari gez.
const PAGE_SIZE = 50;
let sensorsPage = 1;
let sensorsTotal = 0;

export async function loadSensors(page = 1) {
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
            style="cursor:pointer" data-action="loadSensorDetail" data-id="${s.id}"
            >
            <td>${s.id}</td><td>${s.sensor_type}</td><td>${s.serial_number}</td>
            <td><span class="badge active">${s.status}</span></td>
        </tr>
    `).join('');
    _setBusy('sensorsTable', false);
}

export async function loadSensorDetail(sensorId) {
    const readings = await api(`/api/sensors/${sensorId}/readings?limit=30`) || [];
    const sorted = [...readings].reverse();
    if (sensorDetailChart) sensorDetailChart.destroy();
    sensorDetailChart = new Chart(document.getElementById('sensorDetailChart'), {
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
