import asyncio
from math import ceil
from pathlib import Path
from typing import overload, Literal

from playwright.async_api import async_playwright, BrowserContext
from scraper_utils.constants.time_constant import MS1000
from scraper_utils.enums.browser_enum import ResourceType
from scraper_utils.exceptions.browser_exception import PlaywrightError
from scraper_utils.utils.browser_util import abort_resources
from scraper_utils.utils.json_util import write_json
from scraper_utils.utils.time_util import now_str

from emag_crawler.handlers.category_page import (
    goto_category_page,
    category_handler,
    get_product_count_of_category,
)
from emag_crawler.logger import logger as _logger
from emag_crawler.utils import build_category_page_url


cwd = Path.cwd()
today = now_str('%m%d')


async def main():
    async with async_playwright() as pwr:
        _cdp_url = 'http://localhost:9222'
        while True:
            try:
                browser = await pwr.chromium.connect_over_cdp(_cdp_url, timeout=MS1000)
            except PlaywrightError as pe:
                _logger.error(f'无法连接至 CDP "{_cdp_url}"')
                input('确认 CDP 启动后继续...')
                continue
            else:
                break

        context = browser.contexts[0]
        context.set_default_navigation_timeout(0)
        context.set_default_timeout(5 * MS1000)
        await abort_resources(
            context,
            (ResourceType.IMAGE, ResourceType.MEDIA, ResourceType.FONT),
        )

        ########## 输入 ##########
        category = 'veioze-si-lampi'
        first_page_url = 'https://www.emag.ro/veioze-si-lampi/c'
        ########## 输入 ##########

        # 爬取第 1 页
        product_count = await run_crawler(context, category, first_page_url, 1)
        max_page_num = min(5, ceil(product_count / 60))
        _logger.debug(f'"{category}" 共有 {product_count} 个产品，最多爬取至第 {max_page_num} 页')

        # 爬取 2-[5] 页
        for i in range(2, max_page_num + 1):
            await run_crawler(context, category, first_page_url, i)


@overload
async def run_crawler(
    context: BrowserContext, category: str, first_page_url: str, page_num: Literal[1] = 1
) -> int: ...


@overload
async def run_crawler(context: BrowserContext, category: str, first_page_url: str, page_num: int) -> None: ...


async def run_crawler(context: BrowserContext, category: str, first_page_url: str, page_num: int = 1):
    """
    爬取+保存爬取结果

    如果爬取的是第 1 页，会返回该类目有多少个产品
    """

    logger = _logger.bind(category=category)
    logger.info(f'爬取 "{category}" 的第 {page_num} 页')

    if page_num == 1:
        page = await goto_category_page(context, first_page_url, logger)
    else:
        page = await goto_category_page(context, build_category_page_url(first_page_url, page_num), logger)

    product_count = 0
    if page_num == 1:
        try:
            product_count = await get_product_count_of_category(page)
        except BaseException as be:
            logger.error(f'尝试解析 "{category}" 的产品总数时出错\n{be}')

    try:
        result = await category_handler(page, category, logger)
    except BaseException as be:
        logger.error(f'爬取 "{category}" 的第 {page_num} 页时出错\n{be}')
    else:
        logger.info(f'保存 "{category}" 的第 {page_num} 页的爬取结果')
        save_path = await write_json(
            cwd / f'temp/{category}/{today}/{page_num}.json',
            [_.model_dump() for _ in result],
            True,
            indent=4,
        )
        logger.success(f'"{category}" 的第 {page_num} 页的爬取结果已保存至 "{save_path}"')

    if page_num == 1:
        return product_count


if __name__ == '__main__':
    _logger.info('程序启动')
    asyncio.run(main())
    _logger.info('程序结束')
