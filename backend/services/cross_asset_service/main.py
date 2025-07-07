import httpx
import asyncio
import json
from fastapi import FastAPI, BackgroundTasks
from core.config import settings
from core.database import redis_cache

app = FastAPI(title="Cross-Asset Indicators Service")
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

async def fetch_bond_spreads():
    series_id = "BAMLH0A0HYM2" # BofA US High Yield Index Option-Adjusted Spread
    params = {
        "series_id": series_id, "api_key": settings.FRED_API_KEY, "file_type": "json",
        "limit": 12, "sort_order": "desc",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(FRED_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        history = [float(obs["value"]) for obs in data["observations"] if obs["value"] != "."]
        current_value, previous_value = history[0], history[1]
        status = "bearish" if current_value > previous_value else "bullish"

        processed_data = {
            "name": "High-Yield Spreads", "value": f"{current_value:.2f}%", "status": status,
            "description": "Extra yield investors demand for risky corporate bonds.",
            "history": [{"name": obs["date"], "value": float(obs["value"])} for obs in reversed(data["observations"]) if obs["value"] != "."]
        }
        await redis_cache.set(f"indicator:High-Yield Spreads", json.dumps(processed_data))

async def fetch_gold_price():
    params = {"function": "COMMODITIES", "interval": "monthly", "commodities":"GOLD", "apikey": settings.ALPHA_VANTAGE_API_KEY}
    async with httpx.AsyncClient() as client:
        response = await client.get(ALPHA_VANTAGE_URL, params=params)
        response.raise_for_status()
        data = response.json()['data']
        current_value = float(data[0]['price'])
        processed_data = {
            "name": "Gold Price", "value": f"${current_value:,.2f}", "status": "neutral",
            "description": "A traditional safe-haven asset.",
            "history": [{"name": d['date'], "value": float(d['price'])} for d in reversed(data[:12])]
        }
        await redis_cache.set(f"indicator:Gold Price", json.dumps(processed_data))

async def update_cache():
    await asyncio.gather(fetch_bond_spreads(), fetch_gold_price(), return_exceptions=True)

@app.post("/update-cache")
async def trigger_update_cache(background_tasks: BackgroundTasks):
    background_tasks.add_task(update_cache)
    return {"message": "Cross-asset indicators cache update triggered."}

@app.get("/indicators")
async def get_all_cross_asset_indicators():
    keys = ["High-Yield Spreads", "Gold Price"]
    cached_results = await redis_cache.mget([f"indicator:{key}" for key in keys])
    final_data = {}
    key_map = {"High-Yield Spreads": "bondSpreads", "Gold Price": "gold"}
    for data in cached_results:
        if data:
            indicator_data = json.loads(data)
            final_key = key_map.get(indicator_data["name"])
            if final_key:
                final_data[final_key] = indicator_data
    return final_data
