/**
 * SFDAP Dashboard — saf HTML render helper'ları (fixroll_v9b-2).
 *
 * main.js'ten extract edildi. İkisi de saf: `data`/`d` girer, HTML string
 * döner — hiçbir mutable page-state'e (currentUser/sensorsPage vb.) dokunmaz.
 * Buton/aksiyon HTML'i data-action attribute'leri içerir; event delegation
 * (main.js) bunları yakalar.
 */

import { _escAttr, _fmtDate, _fmtNumber, _STATUS_EMOJI, _STATUS_LABEL } from "./utils.js";

export function renderFieldDetail(d) {
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

export function renderPlantResult(data) {
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
