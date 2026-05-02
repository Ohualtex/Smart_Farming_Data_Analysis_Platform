"""
Analitik verilerin disariya aktarilmasini (export) saglayan servis modulu.
Miraç Duran tarafindan Cycle 6 kapsaminda eklendi.
"""

import io
from datetime import datetime

import pandas as pd
from fpdf import FPDF


def _clean_tr(text: str) -> str:
    """FPDF temel fontlari icin Turkce karakterleri temizler."""
    if not isinstance(text, str):
        return str(text)
    replacements = {
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
    }
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    return text


class ReportService:
    """PDF ve Excel formatlarinda rapor ureten servis sinifi."""

    @staticmethod
    def generate_excel_report(data: dict) -> io.BytesIO:
        """Analitik verisini Excel formatina cevirir."""
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # 1. Genel Ozet
            counts_df = pd.DataFrame([data.get("counts", {})])
            counts_df.to_excel(writer, sheet_name="Genel Ozet", index=False)

            # 2. Ciftlik Hava Durumu
            weather_data = data.get("farm_weather_comparison", [])
            # Icerideki dict'leri flatten etmek icin
            flat_weather = []
            for w in weather_data:
                flat_weather.append(
                    {
                        "Farm ID": w.get("farm_id"),
                        "Farm Name": w.get("farm_name"),
                        "City": w.get("city"),
                        "Temp Avg (C)": w.get("temperature", {}).get("avg"),
                        "Humidity Avg (%)": w.get("humidity", {}).get("avg"),
                        "Precipitation (mm)": w.get("precipitation_total_mm"),
                        "Records": w.get("record_count"),
                    }
                )
            pd.DataFrame(flat_weather).to_excel(writer, sheet_name="Hava Durumu", index=False)

            # 3. Sensor Dagilimi
            sensor_df = pd.DataFrame(data.get("sensor_type_distribution", []))
            sensor_df.to_excel(writer, sheet_name="Sensor Dagilimi", index=False)

            # 4. NPK Profilleri
            npk_df = pd.DataFrame(data.get("npk_profiles", []))
            npk_df.to_excel(writer, sheet_name="NPK Profilleri", index=False)

        output.seek(0)
        return output

    @staticmethod
    def generate_pdf_report(data: dict) -> io.BytesIO:
        """Analitik verisini PDF formatina cevirir."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)

        # Baslik
        pdf.cell(0, 10, "Smart Farming Data Analysis Platform (SFDAP)", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("helvetica", "", 12)
        pdf.cell(
            0, 10, f"Analitik Raporu - Son {data.get('period_days', 30)} Gun", new_x="LMARGIN", new_y="NEXT", align="C"
        )
        pdf.cell(
            0,
            10,
            f"Olusturulma Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        pdf.ln(10)

        # 1. Genel Istatistikler
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "1. Genel Istatistikler", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 12)
        counts = data.get("counts", {})

        pdf.cell(0, 8, f"- Kullanici Sayisi: {counts.get('users', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"- Ciftlik Sayisi: {counts.get('farms', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"- Sensor Sayisi: {counts.get('sensors', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"- Toplam Sensor Okumasi: {counts.get('readings', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"- Sulama Programlari: {counts.get('irrigation_schedules', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # 2. Ciftlik Hava Durumu Ozeti
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "2. Ciftlik Hava Durumu Ozeti", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 12)

        for w in data.get("farm_weather_comparison", []):
            name = _clean_tr(w.get("farm_name", ""))
            city = _clean_tr(w.get("city", ""))
            temp = w.get("temperature", {}).get("avg", "N/A")
            hum = w.get("humidity", {}).get("avg", "N/A")
            pdf.cell(0, 8, f"- {name} ({city}): Sicaklik {temp} C, Nem {hum}%", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)

        # 3. Sensor Okuma Istatistikleri
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "3. Sensor Ortalamalari", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 12)
        stats = data.get("sensor_reading_stats", {})
        moisture = stats.get("moisture", {}).get("avg", "N/A")
        soil_temp = stats.get("soil_temperature", {}).get("avg", "N/A")

        pdf.cell(0, 8, f"- Ortalama Toprak Nemi: {moisture}%", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"- Ortalama Toprak Sicakligi: {soil_temp} C", new_x="LMARGIN", new_y="NEXT")

        # Return as BytesIO
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        return output
