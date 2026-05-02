from datetime import UTC, datetime, timedelta


def test_analytics_export_pdf_returns_200_and_pdf(client):
    response = client.get("/api/analytics/export?format=pdf&days=30")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in response.headers["content-disposition"]


def test_analytics_export_xlsx_returns_200_and_excel(client):
    response = client.get("/api/analytics/export?format=xlsx&days=30")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment; filename=" in response.headers["content-disposition"]


def test_analytics_export_invalid_format_returns_400(client):
    response = client.get("/api/analytics/export?format=invalid")
    assert response.status_code == 400


def test_analytics_compare_returns_200(client):
    now = datetime.now(UTC)
    start1 = (now - timedelta(days=60)).isoformat().replace("+", "%2B")
    end1 = (now - timedelta(days=30)).isoformat().replace("+", "%2B")
    start2 = (now - timedelta(days=30)).isoformat().replace("+", "%2B")
    end2 = now.isoformat().replace("+", "%2B")

    response = client.get(
        f"/api/analytics/compare?start_date_1={start1}&end_date_1={end1}&start_date_2={start2}&end_date_2={end2}"
    )

    print("DEBUG:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert "period_1" in data
    assert "period_2" in data
    assert "comparison" in data
    assert "temp_avg_diff_percent" in data["comparison"]
