/* ════════════════════════════════════════════════════════════════
   i18n — backend enum değerlerini Türkçe etikete çevirir.
   Bilinmeyen değer → değerin kendisi (fallback); null/boş → '—'.
   ════════════════════════════════════════════════════════════════ */
const _map = (m) => (v) => (v == null || v === '' ? '—' : (m[String(v).toLowerCase()] ?? String(v)));

// Uyarı + hastalık şiddeti (low/medium/critical + none/low/medium/high)
export const severityLabel = _map({
    none: 'Yok', low: 'Düşük', medium: 'Orta', high: 'Yüksek', critical: 'Kritik',
});

// Uyarı tipi
export const alertTypeLabel = _map({
    low_moisture: 'Düşük nem', disease_reminder: 'Hastalık hatırlatması', model_drift: 'Model sapması',
});

// Sulama durumu
export const irrigationStatusLabel = _map({
    pending: 'Beklemede', completed: 'Tamamlandı', cancelled: 'İptal', scheduled: 'Planlandı',
});

// Audit fix (#27): sensör tipi — daha önce ham snake_case render ediliyordu.
// charts.js'teki typeLabels'ı yansıtır + field-detail form seçenekleri.
export const sensorTypeLabel = _map({
    soil_moisture: 'Toprak Nemi', soil_temperature: 'Toprak Sıcaklığı',
    humidity: 'Hava Nemi', electrical_conductivity: 'Elektriksel İletkenlik',
});

// Audit fix (#27): sensör durumu — daha önce ham İngilizce render ediliyordu.
export const sensorStatusLabel = _map({
    active: 'Aktif', inactive: 'Pasif', maintenance: 'Bakımda', faulty: 'Arızalı',
});

// Hastalık tanısı (ML sınıfları)
export const diagnosisLabel = _map({
    healthy: 'Sağlıklı', leaf_spot: 'Yaprak lekesi', powdery_mildew: 'Külleme', rust: 'Pas',
    blight: 'Yanıklık', mosaic_virus: 'Mozaik virüsü', bacterial_wilt: 'Bakteriyel solgunluk', anthracnose: 'Antraknoz',
});
