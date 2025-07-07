import httpx
import asyncio
import json
import pandas as pd
from fastapi import FastAPI, BackgroundTasks
from core.config import settings
from core.database import redis_cache

app = FastAPI(title="Technical & Market Internals Service")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

async def fetch_moving_averages():
    params = {
        "function": "TIME_SERIES_DAILY", "symbol": "SPY", "outputsize": "full",
        "apikey": settings.ALPHA_VANTAGE_API_KEY
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(ALPHA_VANTAGE_URL, params=params)
        response.raise_for_status()
        data = response.json().get('Time Series (Daily)', {})
        if not data: return

        df = pd.DataFrame.from_dict(data, orient='index', dtype=float)
        df.index = pd.to_datetime(df.index)
        df['50D_MA'] = df['4. close'].rolling(window=50).mean()
        df['200D_MA'] = df['4. close'].rolling(window=200).mean()
        latest = df.iloc[0]
        
        status, value = ("bullish", "Golden Cross") if latest['50D_MA'] > latest['200D_MA'] else ("bearish", "Death Cross")
        
        history = df.iloc[:60].iloc[::-1] # last 60 days, reversed
        processed_data = {
            "name": "50-Day vs 200-Day MA", "value": value, "status": status,
            "description": "The long-term trend of the S&P 500 (SPY).",
            "history": [{"name": i.strftime('%Y-%m-%d'), "50D": r['50D_MA'], "200D": r['200D_MA']} for i, r in history.iterrows() if pd.notna(r['200D_MA'])]
        }
        await redis_cache.set(f"indicator:50-Day vs 200-Day MA", json.dumps(processed_data))

async def update_cache():
    await asyncio.gather(fetch_moving_averages(), return_exceptions=True)

@app.post("/update-cache")
async def trigger_update_cache(background_tasks: BackgroundTasks):
    background_tasks.add_task(update_cache)
    return {"message": "Technicals indicators cache update triggered."}

@app.get("/indicators")
async def get_all_technicals_indicators():
    keys = ["50-Day vs 200-Day MA"]
    cached_results = await redis_cache.mget([f"indicator:{key}" for key in keys])
    final_data = {}
    key_map = {"50-Day vs 200-Day MA": "movingAverages"}
    for data in cached_results:
        if data:
            indicator_data = json.loads(data)
            final_key = key_map.get(indicator_data["name"])
            if final_key:
                final_data[final_key] = indicator_data
    return final_data
