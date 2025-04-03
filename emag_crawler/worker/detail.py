"""操作详情页"""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.async_api import Error as PlaywrightError

from ..logger import logger
from ..utils import build_detail_url

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page


async def goto_detail_page(context: BrowserContext, pnk: str) -> Page:
    """根据 pnk 打开详情页"""
    page = await context.new_page()

    url = build_detail_url(pnk)
    while True:
        logger.info(f'访问 "{url}"')
        try:
            response = await page.goto(url)
        except PlaywrightError as pe:
            logger.warning(f'访问 "{url}" 时出错，即将重试\n{pe}')
            continue
        else:
            if response is None:
                logger.error(f'访问 "{url}" 时响应为空')
                input('响应体为空，按 Enter 继续...')
                continue
            if response.status == 511:
                logger.warning(f'访问 "{url}" 时触发验证')
                input('触发验证，验证通过后按 Enter 继续...')
                continue
            break

    return page


async def crawl_detail(browser: Browser, pnk: str):
    """根据 pnk 爬取该产品的详情页"""
    # TODO 爬取最早评论时间、最新 3 条评论时间、尺寸、重量、最大可加购数
