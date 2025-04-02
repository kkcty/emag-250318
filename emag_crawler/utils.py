from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import re
from time import perf_counter
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright
from scraper_utils.exceptions.browser_exception import PlaywrightError


if TYPE_CHECKING:
    from typing import AsyncGenerator

    from playwright.async_api import Browser, Page


async def wait_for_networkidle(page: Page, timeout: int) -> None:
    """等待页面出现至少 `timeout` 毫秒的网络空闲"""
    start_time = perf_counter()
    while True:
        if perf_counter() - start_time > timeout / 1000:
            break

        try:
            async with page.expect_request(lambda r: True, timeout=timeout):
                pass
        except PlaywrightError:
            try:
                async with page.expect_request_finished(lambda r: True, timeout=timeout):
                    pass
            except PlaywrightError:
                break
            else:
                start_time = perf_counter()
                continue
        else:
            start_time = perf_counter()
            continue


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


@asynccontextmanager
async def connect_cdp(cdp_url: str, timeout: int = 10_000, slow_mo: int = 0) -> AsyncGenerator[Browser]:
    """连接到 CDP"""
    async with async_playwright() as pwr:
        browser = await pwr.chromium.connect_over_cdp(cdp_url, timeout=timeout, slow_mo=slow_mo)
        try:
            yield browser
        finally:
            if browser.is_connected():
                await browser.close()


async def hide_cookie_banner(page: Page) -> None:
    """隐藏类目页、详情页的 Cookie 提醒"""
    await page.add_init_script(
        script="""// 自动隐藏 eMAG 的 cookie 提示
itv = null;

function hideCookieBanner() {
    const xpath = '//div[starts-with(@class, "gdpr-cookie-banner")]';
    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);

    if (result.singleNodeValue) {
        result.singleNodeValue.style.visibility = 'hidden';
        // 隐藏成功后停止执行
        clearInterval(itv);
    }
}

// 在DOM加载完成后立即执行
document.addEventListener('DOMContentLoaded', hideCookieBanner);

// 每500ms检查一次（应对动态加载内容）
itv = setInterval(hideCookieBanner, 500);"""
    )
