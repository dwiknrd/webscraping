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
from urllib.parse import urlparse

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
    path = url_path
    if path.startswith('http'):
        parsed_url = urlparse(path)
        path = parsed_url.path
    regex = r"^[^\s]+/(?P<id>\d+)-(?P<slug>[\w-]+)$"
    group = re.match(regex, path)
    if not group:
        return None, None, path
    return group['id'], group['slug'], path

async def get_product_data(url, content):
    id_, slug_, path = await extract_id_slug(url)

    data = {
        'id': id_,
        'slug': slug_,
        'path': path,
    }

    #parse title
    titleEl = content.find('.design-title', first=True)
    title = None
    if titleEl == None:
        return data
    title = titleEl.text
    data['title'] = title

    #parse size
    sizeEl = content.find('#fabric-size', first = True)
    size = None
    if sizeEl != None:
        size = sizeEl.text
    data['size'] = size

    return data

async def get_parsable_html(body_html_str):
    return HTML(html=body_html_str)

async def get_links(html_r):
    fabric_links = [x for x in list(html_r.links) if x.startswith("/en/fabric")]

    datas = []
    for path in fabric_links:
        id_, slug_, _ = await extract_id_slug(path)
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
        await asyncio.sleep(10) #10 second
        body = await session.get_page_source()
        content = await get_parsable_html(body)
        links = await get_links(content)
        product_data = await get_product_data(url, content)

        if start != None:
            end = time.time() - start
            print(f'{i} took {end} seconds')
        # print(body)
        dataset = {
            'links': links,
            'product_data': product_data
        }
        return dataset

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
    print(results)
    end = time.time() - start
    print(f'total time is: {end}')

    # loop = asyncio.get_event_loop()
    # result = loop.run_until_complete(scraper(url))
    # df = asyncio.run(run(url))
    # print(df.head())
