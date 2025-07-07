import asyncio
import httpx
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SERVICE_URLS = {
    "economic": settings.ECONOMIC_SERVICE_URL,
    "sentiment": settings.SENTIMENT_SERVICE_URL,
    "technicals": settings.TECHNICALS_SERVICE_URL,
    "cross_asset": settings.CROSS_ASSET_SERVICE_URL,
}

async def trigger_cache_update(service_name: str, url: str):
    """Makes a POST request to a service's /update-cache endpoint."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            logging.info(f"Triggering cache update for {service_name} service...")
            response = await client.post(f"{url}/update-cache")
            response.raise_for_status()
            logging.info(f"Successfully updated cache for {service_name}: {response.json()}")
        except httpx.RequestError as e:
            logging.error(f"Failed to trigger cache update for {service_name}: {e}")

async def update_all_caches():
    """Triggers cache updates for all services concurrently."""
    tasks = [trigger_cache_update(name, url) for name, url in SERVICE_URLS.items()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_all_caches, 'interval', hours=settings.SCHEDULER_INTERVAL_HOURS, misfire_grace_time=3600)
    
    async def startup():
        await asyncio.sleep(15) # Give services time to start up before initial trigger
        logging.info("Running initial cache update on startup...")
        await update_all_caches()
        
        scheduler.start()
        logging.info(f"Scheduler started. Will run every {settings.SCHEDULER_INTERVAL_HOURS} hours.")

    loop = asyncio.get_event_loop()
    loop.create_task(startup())
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

