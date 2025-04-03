"""处理类目页"""

from __future__ import annotations

import re
from asyncio import CancelledError
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError

from ..logger import logger

if TYPE_CHECKING:
    from typing import Collection

    from playwright.async_api import Page, Response

"""
用 goto 打开的类目页链接，产品数据是放在各个产品卡片里 css=div.card-standard。

点击 css=button.listing-view-type-change 的切换产品展示方式按钮后，
会发起 www.emag.ro/search-by-filters-with-redirect 的请求，并跳转至第 1 页，该请求的响应包含了第 1 页的产品数据。
WARNING Fashion 类目没有切换产品展示方式的按钮

点击底部的换页按钮后，会发起 www.emag.ro/search-by-url 的请求，该请求的响应包含了新页的产品数据。
TODO 对于只有一页产品并且没有切换产品展示方式的类目该怎么解析产品数据？
"""

"""
加购时捕获 newaddtocart 请求，类目页和详情页的加购是同一个请求
响应体中有 error 代表加购失败
products_count 代表购物车内产品数量
"""


async def have_view_type_change_button(page: Page) -> bool:
    """判断有无切换产品展示方式的按钮"""
    view_type_change_button = page.locator('css=button.listing-view-type-change[data-type="2"]')
    return await view_type_change_button.count() > 0


async def is_first_page(page: Page) -> bool:
    """判断当前页面是否为第一页"""
    # 上一页的按钮是否被禁用
    disabled_first_pagination_li = page.locator('css=ul.pagination > li:first-child.disabled')
    return await disabled_first_pagination_li.count() > 0


async def is_last_page(page: Page) -> bool:
    """判断当前页面是否为最后一页"""
    # 下一页的按钮是否被禁用
    disabled_next_pagination_li = page.locator('css=ul.pagination > li:last-child.disabled')
    return await disabled_next_pagination_li.count() > 0


async def is_pagination_gotoable(page: Page, n: int) -> bool:
    """判断能否跳转至指定页码"""
    if n <= 0:
        raise ValueError(f'页码必须为正整数 {n}')

    if await get_current_page_number(page) == n:
        return False

    return n in await get_gotoable_page_numbers(page)


async def get_current_page_number(page: Page) -> int:
    """解析当前页码"""
    active_pagination_a = page.locator('css=ul.pagination > li.active > a[data-page]')
    return int(await active_pagination_a.inner_text(timeout=MS1000))


async def get_gotoable_page_numbers(page: Page) -> Collection[int]:
    """解析当前可跳转至的页码"""
    data_page_as = page.locator('css=ul.pagination > li > a[data-page]')
    data_pages = [await a.get_attribute('data-page', timeout=MS1000) for a in await data_page_as.all()]
    page_numbers = {int(_) for _ in data_pages if _ is not None}
    return page_numbers


async def change_view_type(page: Page) -> Response:
    """切换产品展示方式，并捕获 search-by-filters-with-redirect 请求的响应"""
    while True:
        try:
            async with page.expect_response(
                re.compile(r'emag\.ro/search-by-filters-with-redirect')
            ) as response_event:
                try:
                    await page.locator('css=button.listing-view-type-change[data-type="2"]').click(
                        timeout=MS1000
                    )
                except PlaywrightError as pe:
                    logger.warning(f'切换产品展示方式时出错\n{pe}')
                    response_event._cancel()
        except PlaywrightError as pe:
            logger.warning(f'等待 search-by-filters-with-redirect 请求的响应时出错\n{pe}')
            continue
        except CancelledError:
            continue
        else:
            response = await response_event.value
            if response.status == 511:
                # TODO 待测试
                logger.warning('请求 search-by-filters-with-redirect 时触发验证')
                input('触发验证，验证通过后按 Enter 继续...')
                continue
            return response


async def goto_first_page(page: Page) -> Response:
    """点击第一页的按钮，跳转至第一页，并捕获 search-by-url 请求的响应"""
    while True:
        try:
            async with page.expect_response(re.compile(r'emag\.ro/search-by-url')) as response_event:
                try:
                    await page.locator('css=ul.pagination > li:nth-child(2) > a[data-page="1"]').click(
                        timeout=MS1000
                    )
                except PlaywrightError as pe:
                    logger.warning(f'点击第一页按钮时出错\n{pe}')
                    response_event._cancel()
        except PlaywrightError as pe:
            logger.warning(f'等待 search-by-url 请求的响应时出错\n{pe}')
            continue
        except CancelledError:
            continue
        else:
            response = await response_event.value
            if response.status == 511:
                # TODO 待测试
                logger.warning('请求 search-by-url 时触发验证')
                input('触发验证，验证通过后按 Enter 继续...')
                continue
            return response


async def goto_next_page(page: Page) -> Response:
    """点击下一页的按钮，跳转至下一页，并捕获 search-by-url 请求的响应"""
    while True:
        try:
            async with page.expect_response(re.compile(r'emag\.ro/search-by-url')) as response_event:
                try:
                    await page.locator('css=ul.pagination > li:last-child > a[data-page]').click(
                        timeout=MS1000
                    )
                except PlaywrightError as pe:
                    logger.warning(f'点击下一页按钮时出错\n{pe}')
                    response_event._cancel()
        except PlaywrightError as pe:
            logger.warning(f'等待 search-by-url 请求的响应时出错\n{pe}')
            continue
        except CancelledError:
            continue
        else:
            response = await response_event.value
            if response.status == 511:
                # TODO 待测试
                logger.warning('请求 search-by-url 时触发验证')
                input('触发验证，验证通过后按 Enter 继续...')
                continue
            return response


async def goto_pagination(page: Page, n: int) -> Response:
    """跳转至指定页码，并捕获 search-by-url 请求的响应"""
    logger.info(f'从 "{page.url}" 跳转至第 {n} 页')

    if n <= 0:
        raise ValueError(f'页码必须为正整数 {n}')

    while True:
        try:
            async with page.expect_response(re.compile(r'emag\.ro/search-by-url')) as response_event:
                try:
                    await page.locator(f'css=ul.pagination > li > a[data-page="{n}"]').first.click(
                        timeout=MS1000
                    )
                except PlaywrightError as pe:
                    logger.warning(f'点击第 {n} 页的跳转按钮时出错\n{pe}')
                    response_event._cancel()
        except PlaywrightError as pe:
            logger.warning(f'等待 search-by-url 请求的响应时出错\n{pe}')
            continue
        except CancelledError:
            continue
        else:
            response = await response_event.value
            if response.status == 511:
                # TODO 待测试
                logger.warning('请求 search-by-url 时触发验证')
                input('触发验证，验证通过后按 Enter 继续...')
                continue
            return response
