import asyncio                                                                                                                                                                              
import httpx  

semaphore = asyncio.Semaphore(10) #concurrency limiter set to 10 max at the same time

async def throttled_get(url: str, headers: dict) -> httpx.Response:
    async with semaphore:
        async with httpx.AsyncClient(timeout=30) as client:
            return await client.get(url, headers=headers)
            