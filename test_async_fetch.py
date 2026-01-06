import asyncio
import aiohttp
import os
from gartan_fetch import gartan_login_and_get_session
from async_gartan_fetch import fetch_grid_html_for_date_async
from dotenv import load_dotenv

load_dotenv()

async def test_async_fetch():
    print("Attempting login (sync) to get cookies...")
    sync_session = gartan_login_and_get_session()
    if not sync_session:
        print("Login failed")
        return

    # Transfer cookies to aiohttp
    cookies = sync_session.cookies.get_dict()

    date = "06/01/2026"
    print(f"Attempting async fetch for {date}...")

    async with aiohttp.ClientSession(cookies=cookies) as session:
        html = await fetch_grid_html_for_date_async(session, date)
        if html:
            print(f"Success! HTML length: {len(html)}")
            print("First 200 chars:")
            print(html[:200])
        else:
            print("Async fetch failed")

if __name__ == "__main__":
    asyncio.run(test_async_fetch())
