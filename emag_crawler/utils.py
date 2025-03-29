from __future__ import annotations

import re
from time import perf_counter
from typing import TYPE_CHECKING

from scraper_utils.exceptions.browser_exception import PlaywrightError


if TYPE_CHECKING:
    from playwright.async_api import Page


async def wait_for_networkidle(page: Page, timeout: int) -> None:
    """等待页面一段时间内都没有网络请求"""
    start_time = perf_counter()
    while True:
        if perf_counter() - start_time > timeout / 1000:
            break

        try:
            async with page.expect_request('**', timeout=timeout):
                pass
        except PlaywrightError:
            break
        else:
            start_time = perf_counter()

        try:
            async with page.expect_request_finished(lambda r: True, timeout=timeout):
                pass
        except PlaywrightError:
            break
        else:
            start_time = perf_counter()


def build_category_page_url(first_page_url: str, page: int) -> str:
    """根据类目页第一页的链接构造后续页链接"""
    if page <= 1:
        raise ValueError(f'page={page} 必须大于 1')
    if re.search(r'/p\d+/c', first_page_url) is not None:
        raise ValueError('请传入第一页的链接')

    result = re.sub(r'(?<!\d)/c(?=\?|/|$)', f'/p{page}/c', first_page_url)
    if result == first_page_url:
        raise ValueError('正则表达式匹配失败')
    return result
