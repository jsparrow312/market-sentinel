import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

# Import the core functions from each service that we want to test
from services.economic_service.main import fetch_and_cache_indicator as fetch_economic
from services.sentiment_service.main import fetch_vix
from services.technicals_service.main import fetch_moving_averages
from services.cross_asset_service.main import fetch_bond_spreads

# Use pytest-asyncio to handle async functions
pytestmark = pytest.mark.asyncio

@patch('services.economic_service.main.redis_cache', new_callable=AsyncMock)
@patch('services.economic_service.main.httpx.AsyncClient')
async def test_economic_service_yield_curve_inversion(mock_client, mock_redis):
    """Tests if the economic service correctly identifies an inverted yield curve."""
    # Arrange
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "observations": [{"value": "-0.25"}, {"value": "0.1"}]
    }
    mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

    # Act
    result = await fetch_economic("T10Y2Y", "Yield Curve", "Test Desc")

    # Assert
    assert result["status"] == "bearish"
    assert result["value"] == "-0.25"
    mock_redis.set.assert_called_once()

@patch('services.sentiment_service.main.redis_cache', new_callable=AsyncMock)
@patch('services.sentiment_service.main.httpx.AsyncClient')
async def test_sentiment_service_vix_complacency(mock_client, mock_redis):
    """Tests if the sentiment service correctly identifies a low VIX (complacency)."""
    # Arrange
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"value": "12.5"}, {"value": "13.0"}]
    }
    mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

    # Act
    result = await fetch_vix()

    # Assert
    assert result["status"] == "bullish" # Low VIX is a contrarian bearish signal, but the direct status is bullish (low fear)
    assert result["value"] == "12.50"
    mock_redis.set.assert_called_once()


@patch('services.technicals_service.main.redis_cache', new_callable=AsyncMock)
@patch('services.technicals_service.main.httpx.AsyncClient')
async def test_technicals_service_death_cross(mock_client, mock_redis):
    """Tests if the technicals service correctly identifies a Death Cross."""
    # Arrange
    mock_response = MagicMock()
    mock_api_data = {"Time Series (Daily)": {}}
    for i in range(200):
        # Create data where recent prices are lower, forcing 50D < 200D
        price = 400 + (i * 0.1) if i < 50 else 500
        mock_api_data["Time Series (Daily)"][f"2025-07-{200-i:02d}"] = {"4. close": str(price)}
    mock_response.json.return_value = mock_api_data
    mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

    # Act
    await fetch_moving_averages()

    # Assert
    args, kwargs = mock_redis.set.call_args
    cached_data = json.loads(args[1])
    assert cached_data['status'] == 'bearish'
    assert cached_data['value'] == 'Death Cross'

@patch('services.cross_asset_service.main.redis_cache', new_callable=AsyncMock)
@patch('services.cross_asset_service.main.httpx.AsyncClient')
async def test_cross_asset_service_widening_spreads(mock_client, mock_redis):
    """Tests if the cross-asset service correctly identifies widening bond spreads."""
    # Arrange
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "observations": [{"value": "4.5"}, {"value": "4.2"}] # Current is higher than previous
    }
    mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

    # Act
    result = await fetch_bond_spreads()

    # Assert
    assert result["status"] == "bearish"
    assert result["value"] == "4.50%"
    mock_redis.set.assert_called_once()
