"""
Health Endpoint Testleri
========================
GET /api/health
"""

import pytest


def test_health_check_returns_200(client):
    """Health endpoint 200 döndürmeli."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_check_response_structure(client):
    """Health endpoint doğru alanları döndürmeli."""
    response = client.get("/api/health")
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "version" in data


def test_health_check_status_is_healthy(client):
    """Status değeri 'healthy' olmalı."""
    response = client.get("/api/health")
    assert response.json()["status"] == "healthy"


def test_health_check_service_name(client):
    """Service adı doğru olmalı."""
    response = client.get("/api/health")
    assert response.json()["service"] == "SFDAP API"


def test_root_endpoint(client):
    """Root endpoint (/) çalışmalı ve docs bilgisi döndürmeli."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data
    assert data["docs"] == "/docs"
