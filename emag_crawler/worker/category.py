"""操作类目页"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pathlib import Path
from playwright.async_api import Error as PlaywrightError
from scraper_utils.utils.browser_util import ResourceType, abort_resources
from scraper_utils.utils.json_util import write_json_async
from scraper_utils.utils.time_util import now_str

from ..handlers.category import is_first_page, is_last_page, is_pagination_gotoable, goto_pagination
from ..logger import logger
from ..parsers.category import parse_search_by_url_response

if TYPE_CHECKING:
    from typing import Any

    from playwright.async_api import Browser, BrowserContext, Page


cwd = Path.cwd()


async def goto_category_page(context: BrowserContext, url: str) -> Page:
    """打开类目页"""
    page = await context.new_page()

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


async def crawl_category(browser: Browser, url: str):
    """开始爬取一个类目"""
    context = await browser.new_context(no_viewport=True)

    context.set_default_navigation_timeout(0)
    await abort_resources(
        context,
        res_types=(
            ResourceType.STYLESHEET,
            ResourceType.FONT,
            ResourceType.IMAGE,
            ResourceType.MEDIA,
        ),
    )

    page = await goto_category_page(context, url)

    results: list[dict[str, Any]] = list()
    category_id = '-'

    # 如果不是第 1 页
    if await is_first_page(page) is False:
        for i in range(1, 5 + 1):
            if is_pagination_gotoable(page, i):
                response = await goto_pagination(page, i)
                response_json = await response.json()
                result = parse_search_by_url_response(response_json)
                if i == 1:
                    category_id = result['id']
                results.append(result)

    # 如果是第 1 页
    else:
        # 如果是末页（这个类目只有 1 页）
        if await is_last_page(page):
            pass  # TODO 类目只有 1 页的还没做

        # 这个类目不止 1 页
        else:
            for i in (2, 3, 4, 5, 1):
                if await is_pagination_gotoable(page, i):
                    response = await goto_pagination(page, i)
                    response_json = await response.json()
                    result = parse_search_by_url_response(response_json)
                    if i == 1:
                        category_id = result['id']
                    results.append(result)

    # 将结果按页码排序
    results.sort(key=lambda d: d['current_page_number'])

    json_save_dir = cwd / f'output/{category_id}'
    json_save_dir.mkdir(parents=True, exist_ok=True)
    json_save_path = json_save_dir / f'{now_str('%Y%m%d_%H%M%S')}.json'
    await write_json_async(json_save_path, results, indent=2)
