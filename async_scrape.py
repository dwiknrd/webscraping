import os
import asyncio
from arsenic import get_session, keys, browsers, services
import pandas as pd
from requests_html import HTML 
import itertools
import re
import time
import pathlib


async def extract_id_slug(url_path):
    regex = r"^[^\s]+/(?P<id>\d+)-(?P<slug>[\w-]+)$"
    group = re.match(regex, url_path)
    if not group:
        return None, None
    return group['id'], group['slug']


async def scraper(url):
    service = services.Chromedriver()
    browser = browsers.Chrome(chromeOption={
        'args': ['--headless', '--disable-gpu']
    })

    async with get_session(service, browser) as session:
        await session.get(url)
        body = await session.get_page_source()
        return body
        

if __name__ == "__main__":
    url = 'https://www.spoonflower.com/en/shop?on=fabric'
    # loop = asyncio.get_event_loop()
    # result = loop.run_until_complete(scraper(url))
    result = asyncio.run(scraper(url))
