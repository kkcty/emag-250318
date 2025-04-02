"""测试"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import re
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright, Error as PlaywrightError
from scraper_utils.constants.time_constant import MS1000
from scraper_utils.utils.json_util import write_json_async

from emag_crawler.handlers.category import goto_category_page, parse_card_items, parse_category


if TYPE_CHECKING:
    from typing import AsyncGenerator

    from playwright.async_api import Browser


@asynccontextmanager
async def connect_cdp(cdp_url: str = 'http://localhost:9222') -> AsyncGenerator[Browser]:
    """连接到 CDP"""
    async with async_playwright() as pwr:
        while True:
            try:
                browser = await pwr.chromium.connect_over_cdp(cdp_url, timeout=1_000)
            except PlaywrightError:
                input('确认 CDP 启动后继续...')
                continue
            else:
                break

        try:
            yield browser
        finally:
            await browser.close()


async def start_crawl():
    async with connect_cdp() as browser:
        context = await browser.new_context(no_viewport=True)
        context.set_default_navigation_timeout(0)

        page = await goto_category_page(context, 'https://www.emag.ro/seturi-constructie/p2/c')

        # products = await parse_card_items(page)
        # await write_json_async('temp/products-p2.json', [_.model_dump() for _ in products], indent=4)

        # category = await parse_category(page)
        # await write_json_async('temp/category-p2.json', category.model_dump(), indent=4)

        # input('Enter...')

        # TEMP
        print(page.url)
        next_page_a = page.locator('css=a.js-change-page[aria-label="Next"]')
        async with page.expect_navigation(
            url=re.compile(r'www\.emag\.ro/.*?/p\d+/c'),
        ) as response_event:
            print('点击下一页按钮')
            await next_page_a.click(timeout=MS1000)
        response = await response_event.value
        # if response.status == 511:
        #     print('遇到验证')
        print(page.url)

        input('Enter...')


def main():
    asyncio.run(start_crawl())


if __name__ == '__main__':
    main()
