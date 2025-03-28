"""处理购物车页"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError

from ..models import ProductCardItem
from ..utils import wait_for_networkidle

if TYPE_CHECKING:
    from loguru import Logger
    from playwright.async_api import BrowserContext, Page, Locator


async def goto_cart_page(context: BrowserContext, logger: Logger) -> Page:
    """打开购物车页"""
    logger.info('打开购物车页')

    page = await context.new_page()

    while True:
        try:
            response = await page.goto('https://www.emag.ro/cart/products', wait_until='networkidle')
        except PlaywrightError:
            pass
        else:
            if response is None or response.status == 511:
                input('等待验证...')
                continue
            break

    return page


async def clear_cart(page: Page, logger: Logger) -> None:
    """清空购物车"""
    logger.info('清空购物车')

    # TODO 如何保证在触发验证后能暂停，并在通过验证后从暂停点继续？

    cart_widget_divs = page.locator('css=div.cart-widget[data-id]')

    while await cart_widget_divs.count() > 0:
        while await cart_widget_divs.locator('css=div.preloader').count() > 0:
            await asyncio.sleep(1)

        if await cart_widget_divs.count() == 0:
            break

        logger.debug(f'正在清空购物车，剩余 {await cart_widget_divs.count()} 个产品')

        try:
            await cart_widget_divs.locator('css=button.btn-remove-product').filter(visible=True).last.click(
                timeout=MS1000
            )
        except PlaywrightError:
            pass

    logger.info('等待所有清购请求完成')
    # await page.wait_for_load_state('networkidle')
    await wait_for_networkidle(page, 10 * MS1000)


async def parse_max_qtys(page: Page, products: list[ProductCardItem], logger: Logger) -> None:
    """解析购物车内的所有产品数据"""
    logger.info('解析产品最大可加购数')

    cart_widget_divs = page.locator('css=div.cart-widget[data-id]')

    qtys: dict[str, int] = dict()
    for i in range(await cart_widget_divs.count()):
        data_id, max_qty = await parse_max_qty(cart_widget_divs.nth(i))
        logger.debug(f'解析到 data-id={data_id} 的最大可加购数 {max_qty}')
        qtys[data_id] = max_qty

    for p in products:
        # 跳过 qty 已经解析了的产品
        if p.max_qty is not None:
            continue

        p.max_qty = qtys.get(p.product_id, None)
        if p.max_qty is not None:
            p.cart_added = p.max_qty is not None
            logger.debug(
                f'找到已加购产品 #{p.rank_in_page} pnk="{p.pnk}" data-id={p.product_id} 的最大可加购数 {p.max_qty}'
            )
        else:
            logger.warning(
                f'购物车内未找到已加购产品 #{p.rank_in_page} pnk="{p.pnk}" data-id={p.product_id} 的最大可加购数'
            )


async def parse_max_qty(cart_widget_div: Locator) -> tuple[str, int]:
    """解析单个产品的最大可加购数"""

    data_id: str = await cart_widget_div.get_attribute('data-id', timeout=MS1000)  # type: ignore
    data_id = re.search(r'_?(\d+)$', data_id).group(1)  # type: ignore

    max_qty_inputs = cart_widget_div.locator('css=input[max]')
    max_qty = int(await max_qty_inputs.first.get_attribute('max', timeout=MS1000))  # type: ignore

    return data_id, max_qty
