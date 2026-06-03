import { api } from "./api.js";
import { showToast, escAttr as _escAttr } from "./ui_helpers.js";

// ─── FERTILIZER ───────────────────────────────────────────────
export async function recommendFertilizer() {
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

export async function fertilizerSchedule() {
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
