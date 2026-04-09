import asyncio                                                                                                                                                                              
import httpx  

semaphore = asyncio.Semaphore(10)

async def throttled_get(url: str, headers: dict) -> httpx.Response:
    async with semaphore:
        async with httpx.AsyncClient() as client:
            return await client.get(url, headers=headers)   
            