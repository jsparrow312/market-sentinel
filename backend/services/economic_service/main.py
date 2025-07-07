import httpx
import asyncio
import json
from fastapi import FastAPI, BackgroundTasks
from core.config import settings
from core.database import redis_cache

app = FastAPI(title="Economic Indicators Service")
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"

async def fetch_and_cache_indicator(series_id: str, name: str, description: str):
    """Fetches data, processes it, and stores it in the Redis cache."""
    params = {
        "series_id": series_id, "api_key": settings.FRED_API_KEY, "file_type": "json",
        "limit": 12, "sort_order": "desc",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(FRED_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        current_value = float(data["observations"][0]["value"])
        status = "neutral"
        if series_id == "T10Y2Y": status = "bearish" if current_value < 0 else "bullish"
        elif series_id == "NAPM": status = "bullish" if current_value > 50 else "bearish"

        processed_data = {
            "name": name, "value": f"{current_value:.2f}", "status": status,
            "description": description,
            "history": [{"name": obs["date"], "value": float(obs["value"])} for obs in reversed(data["observations"]) if obs["value"] != "."]
        }
        await redis_cache.set(f"indicator:{name}", json.dumps(processed_data))
    return processed_data

async def update_cache():
    """The core logic for the scheduler to call."""
    indicator_map = {
        "yieldCurve": ("T10Y2Y", "Yield Curve (10Y vs 2Y)", "Market's expectation for future growth."),
        "ismPmi": ("NAPM", "ISM Manufacturing PMI", "Health of the manufacturing sector."),
        "joblessClaims": ("ICSA", "Initial Jobless Claims", "Health of the labor market."),
    }
    tasks = [fetch_and_cache_indicator(sid, name, desc) for key, (sid, name, desc) in indicator_map.items()]
    await asyncio.gather(*tasks, return_exceptions=True)

@app.post("/update-cache")
async def trigger_update_cache(background_tasks: BackgroundTasks):
    """A non-blocking endpoint for the scheduler to trigger cache updates."""
    background_tasks.add_task(update_cache)
    return {"message": "Economic indicators cache update triggered."}

@app.get("/indicators")
async def get_all_economic_indicators():
    """Fetches all economic indicators directly from the cache."""
    keys = ["Yield Curve (10Y vs 2Y)", "ISM Manufacturing PMI", "Initial Jobless Claims"]
    cached_results = await redis_cache.mget([f"indicator:{key}" for key in keys])
    
    final_data = {}
    key_map = {"Yield Curve (10Y vs 2Y)": "yieldCurve", "ISM Manufacturing PMI": "ismPmi", "Initial Jobless Claims": "joblessClaims"}
    for data in cached_results:
        if data:
            indicator_data = json.loads(data)
            final_key = key_map.get(indicator_data["name"])
            if final_key:
                final_data[final_key] = indicator_data
    return final_data
