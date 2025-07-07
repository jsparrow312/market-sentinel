import httpx
import asyncio
import json
from fastapi import FastAPI, BackgroundTasks
from core.config import settings
from core.database import redis_cache

app = FastAPI(title="Sentiment Indicators Service")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=30"

async def fetch_vix():
    params = {"function": "VIX", "apikey": settings.ALPHA_VANTAGE_API_KEY}
    async with httpx.AsyncClient() as client:
        response = await client.get(ALPHA_VANTAGE_URL, params=params)
        response.raise_for_status()
        data = response.json()['data']
        current_value = float(data[0]['value'])
        status = "bearish" if current_value > 35 else "bullish" if current_value < 15 else "neutral"
        processed_data = {
            "name": "VIX (Fear Gauge)", "value": f"{current_value:.2f}", "status": status,
            "description": "The market's expectation of 30-day volatility.",
            "history": [{"name": d['date'], "value": float(d['value'])} for d in reversed(data[:12])]
        }
        await redis_cache.set(f"indicator:VIX (Fear Gauge)", json.dumps(processed_data))

async def fetch_fear_and_greed():
    async with httpx.AsyncClient() as client:
        response = await client.get(FEAR_GREED_URL)
        response.raise_for_status()
        data = response.json()['data']
        current_value = int(data[0]['value'])
        status = "bearish" if current_value > 75 else "bullish" if current_value < 25 else "neutral"
        processed_data = {
            "name": "CNN Fear & Greed", "value": str(current_value), "status": status,
            "description": "A composite index of 7 sentiment indicators.",
            "history": [{"name": d['timestamp'], "value": int(d['value'])} for d in reversed(data)]
        }
        await redis_cache.set(f"indicator:CNN Fear & Greed", json.dumps(processed_data))

async def update_cache():
    await asyncio.gather(fetch_vix(), fetch_fear_and_greed(), return_exceptions=True)

@app.post("/update-cache")
async def trigger_update_cache(background_tasks: BackgroundTasks):
    background_tasks.add_task(update_cache)
    return {"message": "Sentiment indicators cache update triggered."}

@app.get("/indicators")
async def get_all_sentiment_indicators():
    keys = ["VIX (Fear Gauge)", "CNN Fear & Greed"]
    cached_results = await redis_cache.mget([f"indicator:{key}" for key in keys])
    final_data = {}
    key_map = {"VIX (Fear Gauge)": "vix", "CNN Fear & Greed": "fearGreed"}
    for data in cached_results:
        if data:
            indicator_data = json.loads(data)
            final_key = key_map.get(indicator_data["name"])
            if final_key:
                final_data[final_key] = indicator_data
    return final_data
