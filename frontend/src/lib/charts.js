/**
 * SFDAP Dashboard — Chart.js render helper'ları (fixroll_v9b).
 *
 * main.js'ten extract edildi (window-bridge sonrası modülarizasyon).
 * Tüm fonksiyonlar saf: `data` girer, canvas'a render eder. Paylaşılan
 * `charts` registry'si (Chart instance'larını re-render öncesi destroy
 * etmek için) ve `analyticsColors` paleti burada tek kaynak; main.js
 * inline chart kullanımları (loadSensorDetail/loadWeather/loadFieldReadingsChart)
 * `charts`'ı buradan import eder.
 *
 * Bağımlılık: global `Chart` (Chart.js CDN, index.html'de yüklenir).
 */

// Chart.js instance registry — re-render öncesi eski instance destroy edilir.
export const charts = {};

export const analyticsColors = {
    green: '#10b981', blue: '#3b82f6', amber: '#f59e0b',
    red: '#ef4444', violet: '#8b5cf6', cyan: '#06b6d4',
    pink: '#ec4899', lime: '#84cc16',
};

// Tema-duyarlı grafik renkleri — canvas içi yazı/ızgara (chart OLUŞTURULURKEN okunur,
// sayfa değişiminde yeniden render edilince temaya uyar). Light: koyu yazı + açık ızgara.
const _isLight = () => document.documentElement.dataset.theme === 'light';
// Light: koyu yazı / açık ızgara. Dark: AÇIK yazı (okunur) / koyu ızgara.
export const chartTick = () => (_isLight() ? '#314257' : '#aeb9c9');     // eksen etiketleri
export const chartLegend = () => (_isLight() ? '#1e293b' : '#dbe2ec');   // legend / başlık
export const chartGrid = () => (_isLight() ? 'rgba(20,80,140,.14)' : 'rgba(148,163,184,.16)'); // ızgara

// Tema değişince TÜM kayıtlı grafiklerin canvas-içi renklerini YERİNDE günceller
// (re-render/re-fetch/flash YOK). Accent tick'ler (amber sıcaklık / mavi nem
// data eksenleri) korunur. Toggle anında çağrılır → yazılar yeni temada görünür.
const _ACCENT = new Set(['#f59e0b', '#3b82f6']);
export function rethemeCharts() {
    Object.values(charts).forEach(ch => {
        if (!ch || !ch.options) return;
        const lg = ch.options.plugins?.legend?.labels;
        if (lg) lg.color = chartLegend();
        const ttl = ch.options.plugins?.title;
        if (ttl && ttl.color) ttl.color = chartLegend();
        Object.values(ch.options.scales || {}).forEach(sc => {
            if (!sc) return;
            if (sc.ticks && !_ACCENT.has(sc.ticks.color)) sc.ticks.color = chartTick();
            if (sc.grid && sc.grid.display !== false) sc.grid.color = chartGrid();
            if (sc.pointLabels) sc.pointLabels.color = chartLegend();
            if (sc.title && sc.title.color) sc.title.color = chartTick();
        });
        ch.update('none');
    });
}

export function renderMoistureChart(data) {
    const points = Array.isArray(data) ? data : [];
    const labels = points.map(d => new Date(d.hour).toLocaleString('tr', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }));
    const values = points.map(d => d.moisture_percent);
    if (charts.moisture) charts.moisture.destroy();
    charts.moisture = new Chart(document.getElementById('moistureChart'), {
        type: 'line', data: { labels, datasets: [{ label: 'Toprak Nemi %', data: values, borderColor: '#3b82f6',
            backgroundColor: 'rgba(59,130,246,.1)', fill: true, tension: .4, pointRadius: 2 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: chartLegend() } } },
            scales: { x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } }, y: { ticks: { color: chartTick() }, grid: { color: chartGrid() } } } }
    });
}

export function renderTempHumChart(data) {
    const sorted = [...data].reverse();
    const labels = sorted.map(d => new Date(d.recorded_at).toLocaleDateString('tr'));
    if (charts.tempHum) charts.tempHum.destroy();
    charts.tempHum = new Chart(document.getElementById('tempHumChart'), {
        type: 'line', data: { labels, datasets: [
            { label: 'Sıcaklık °C', data: sorted.map(d => d.temperature_c), borderColor: '#f59e0b', tension: .4, pointRadius: 2, yAxisID: 'y' },
            { label: 'Nem %', data: sorted.map(d => d.humidity_percent), borderColor: '#3b82f6', tension: .4, pointRadius: 2, yAxisID: 'y1' },
        ] },
        options: { responsive: true, plugins: { legend: { labels: { color: chartLegend() } } },
            scales: {
                x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } },
                y: { position: 'left', ticks: { color: '#f59e0b' }, grid: { color: chartGrid() } },
                y1: { position: 'right', ticks: { color: '#3b82f6' }, grid: { display: false } },
            } }
    });
}

export function renderPrecipChart(data) {
    const sorted = [...data].reverse();
    const labels = sorted.map(d => new Date(d.recorded_at).toLocaleDateString('tr'));
    if (charts.precip) charts.precip.destroy();
    charts.precip = new Chart(document.getElementById('precipChart'), {
        type: 'bar', data: { labels, datasets: [{ label: 'Yağış mm', data: sorted.map(d => d.precipitation_mm),
            backgroundColor: 'rgba(6,182,212,.5)', borderColor: '#06b6d4', borderWidth: 1 }] },
        options: { responsive: true, plugins: { legend: { labels: { color: chartLegend() } } },
            scales: { x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } }, y: { ticks: { color: chartTick() }, grid: { color: chartGrid() } } } }
    });
}

export function renderSensorTypeChart(dist) {
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
            plugins: { legend: { position: 'bottom', labels: { color: chartLegend(), padding: 16, font: { size: 12 } } } }
        }
    });
}

export function renderFarmTempChart(comparison) {
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
            plugins: { legend: { labels: { color: chartLegend() } },
                title: { display: true, text: 'Bölge Bazlı Sıcaklık Karşılaştırması', color: chartLegend(), font: { size: 13 } } },
            scales: {
                x: { ticks: { color: chartTick() }, grid: { color: chartGrid() }, title: { display: true, text: '°C', color: chartTick() } },
                y: { ticks: { color: chartLegend(), font: { size: 11 } }, grid: { color: chartGrid() } }
            }
        }
    });
}

export function renderIrrigationStatusChart(dist) {
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
            plugins: { legend: { position: 'bottom', labels: { color: chartLegend(), padding: 16, font: { size: 12 } } } },
            scales: { r: { ticks: { color: chartTick(), backdropColor: 'transparent' }, grid: { color: chartGrid() } } }
        }
    });
}

export function renderNpkRadarChart(profiles) {
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
            plugins: { legend: { position: 'bottom', labels: { color: chartLegend(), padding: 16 } } },
            scales: { r: { ticks: { color: chartTick(), backdropColor: 'transparent' }, grid: { color: chartGrid() }, pointLabels: { color: chartLegend(), font: { size: 11 } } } }
        }
    });
}

export function renderDailyTrendChart(trends) {
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
            plugins: { legend: { labels: { color: chartLegend(), font: { size: 11 } } },
                title: { display: true, text: 'Bölge Bazlı Günlük Sıcaklık Trendi', color: chartLegend(), font: { size: 13 } } },
            scales: {
                x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } },
                y: { ticks: { color: chartTick() }, grid: { color: chartGrid() }, title: { display: true, text: '°C', color: chartTick() } }
            }
        }
    });
}

export function renderSensorStatsChart(stats) {
    if (!stats || !stats.moisture || !stats.soil_temperature || stats.moisture.avg == null) return;
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
            plugins: { legend: { labels: { color: chartLegend() } } },
            scales: {
                x: { ticks: { color: chartTick() }, grid: { color: chartGrid() } },
                y: { ticks: { color: chartTick() }, grid: { color: chartGrid() } }
            }
        }
    });
}
