import httpx
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

app = FastAPI(title="Market Dashboard API Gateway")

# --- Security Setup ---
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    """Validates the API key provided in the request header."""
    if api_key == settings.API_KEY:
        return api_key
    else:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Service Routing ---
async def forward_request(service: str, endpoint: str):
    """Generic function to forward requests to a microservice."""
    service_urls = {
        "economic": settings.ECONOMIC_SERVICE_URL,
        "sentiment": settings.SENTIMENT_SERVICE_URL,
        "technicals": settings.TECHNICALS_SERVICE_URL,
        "cross_asset": settings.CROSS_ASSET_SERVICE_URL,
    }
    service_url = service_urls.get(service)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            url = f"{service_url}/{endpoint}"
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Error communicating with {service} service: {exc}")

@app.get("/api/all", dependencies=[Depends(get_api_key)])
async def get_all_data():
    """Convenience endpoint to fetch all data from cache."""
    tasks = {
        "economic": forward_request("economic", "indicators"),
        "sentiment": forward_request("sentiment", "indicators"),
        "technicals": forward_request("technicals", "indicators"),
        "cross_asset": forward_request("cross_asset", "indicators"),
    }
    results = await asyncio.gather(*tasks.values())
    return dict(zip(tasks.keys(), results))
