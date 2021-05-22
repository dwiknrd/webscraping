import os
import asyncio
from arsenic import get_session, keys, browsers, services
import pandas as pd
from requests_html import HTML 
import itertools
import re
import time
import pathlib
import pickle
import pandas as pd

import logging
import structlog #pip install structlog


def store_links_as_df_pickle(datas=[], name='links2.pkl'):
    new_df = pd.DataFrame(datas)
    og_df = pd.DataFrame([{'id':0}])
    if pathlib.Path(name).exists():
        og_df = pd.read_pickle(name)
    df = pd.concat([og_df, new_df])
    df.reset_index(inplace=True, drop=False)
    df = df[['id', 'slug', 'path', 'scraped']]
    df = df.loc[-df.id.duplicated(keep='first')]
    df.dropna(inplace=True)
    df.to_pickle(name)
    return df

def set_arsenic_log_level(level = logging.WARNING):
    #Create logger
    logger = logging.getLogger('arsenic')

    def logger_factory():
        return logger

    structlog.configure(logger_factory=logger_factory)
    logger.setLevel(level)


async def extract_id_slug(url_path):
    regex = r"^[^\s]+/(?P<id>\d+)-(?P<slug>[\w-]+)$"
    group = re.match(regex, url_path)
    if not group:
        return None, None
    return group['id'], group['slug']

async def get_links(body_content):
    html_r = HTML(html=body_content)
    fabric_links = [x for x in list(html_r.links) if x.startswith("/en/fabric")]

    datas = []
    for path in fabric_links:
        id_, slug_ = await extract_id_slug(path)
        data = {
            'id': id_,
            'slug': slug_,
            'path': path,
            'scraped': 0
        }
        datas.append(data)
    return datas

async def scraper(url, i=-1, timeout=60, start=None):
    service = services.Chromedriver()
    browser = browsers.Chrome()
    browser.capabilities = {
        "goog:chromeOptions": {"args": ["--headless", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]}
    }
    async with get_session(service, browser) as session:
        try:
            await asyncio.wait_for(session.get(url), timeout=timeout)
        except asyncio.TimeoutError:
            return []
        body = await session.get_page_source()
        links = await get_links(body)
        if start != None:
            end = time.time() - start
            print(f'{i} took {end} seconds')
        # print(body)
        return links

async def run(urls, timeout=60, start=None):
    results = []
    for i, url in enumerate(urls):
        results.append(
            asyncio.create_task(scraper(url, i=i, timeout=60, start=start))
        )
    list_of_links = await asyncio.gather(*results)
    return list_of_links

if __name__ == "__main__":
    set_arsenic_log_level()
    start = time.time()
    urls = [
        'https://www.spoonflower.com/en/shop?on=fabric',
        'https://www.spoonflower.com/en/fabric/6444170-catching-fireflies-by-thestorysmith'
    ]
    name = 'link2.pkl'
    results = asyncio.run(run(urls, start=start))
    print(len(results))
    end = time.time() - start
    print(f'total time is: {end}')

    # loop = asyncio.get_event_loop()
    # result = loop.run_until_complete(scraper(url))
    # df = asyncio.run(run(url))
    # print(df.head())
