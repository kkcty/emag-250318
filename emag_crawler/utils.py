from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright
from scraper_utils.exceptions.browser_exception import PlaywrightError

from .logger import logger

if TYPE_CHECKING:
    from typing import AsyncGenerator

    from playwright.async_api import Browser, Page


@asynccontextmanager
async def connect_cdp(cdp: str = 'http://localhost:9222') -> AsyncGenerator[Browser]:
    """连接到 CDP"""
    async with async_playwright() as pwr:
        while True:
            logger.info(f'连接 CDP "{cdp}"')
            try:
                browser = await pwr.chromium.connect_over_cdp(cdp, timeout=1_000)
            except PlaywrightError as pe:
                logger.warning(f'连接 CDP "{cdp}" 时出错\n{pe}')
                input('确认 CDP 启动后按 Enter 继续...')
                continue
            else:
                browser.on('disconnected', lambda b: logger.info(f'已断开 CDP "{cdp}"'))
                break

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


def build_detail_url(pnk: str) -> str:
    """根据 pnk 构造详情页链接"""
    return f'https://www.emag.ro/-/pd/{pnk}'
