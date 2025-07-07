import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from api_gateway.main import app, get_api_key

# Use the TestClient for synchronous testing of the API endpoints
client = TestClient(app)

# --- Mocking Dependencies ---
# This overrides the get_api_key dependency for testing purposes
async def override_get_api_key():
    return "test_key"

app.dependency_overrides[get_api_key] = override_get_api_key

# --- Tests ---
def test_get_all_data_unauthorized():
    # Test without providing the API key header
    response = client.get("/api/all")
    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}

@patch('api_gateway.main.forward_request', new_callable=AsyncMock)
def test_get_all_data_authorized(mock_forward_request):
    # Arrange: Mock the return value of the forwarded requests
    mock_forward_request.side_effect = [
        {"economic_data": "ok"},
        {"sentiment_data": "ok"},
        {"technicals_data": "ok"},
        {"cross_asset_data": "ok"},
    ]
    
    # Act: Call the endpoint with a valid (but fake) API key
    response = client.get("/api/all", headers={"X-API-KEY": "test_key"})
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["economic"] == {"economic_data": "ok"}
    assert data["sentiment"] == {"sentiment_data": "ok"}
    assert mock_forward_request.call_count == 4

@patch('api_gateway.main.httpx.AsyncClient')
def test_forward_request_service_unavailable(mock_client):
    # Arrange: Mock the httpx client to raise a connection error
    mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Connection refused")
    
    # Act
    response = client.get("/api/all", headers={"X-API-KEY": "test_key"})
    
    # Assert
    assert response.status_code == 503
    assert "Error communicating with economic service" in response.json()["detail"]
