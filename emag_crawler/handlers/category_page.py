"""处理类目页"""

from __future__ import annotations

import asyncio
from collections import defaultdict
import re
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError
from scraper_utils.utils.emag_util import clean_product_image_url

from .cart_page import goto_cart_page, parse_max_qtys, clear_cart
from ..models import ProductCardItem
from ..utils import wait_for_networkidle

if TYPE_CHECKING:
    from typing import Optional, Awaitable

    from loguru import Logger
    from playwright.async_api import BrowserContext, Page, Locator, Response, Route


_hide_cookie_banner_js = """// 自动隐藏 eMAG 的 cookie 提示
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


async def goto_category_page(context: BrowserContext, url: str, logger: Logger) -> Page:
    """打开类目页"""
    logger.info(f'打开类目页 "{url}"')

    # NOTICE eMAG 确实能分辨是人工浏览器，还是 CDP

    page = await context.new_page()
    await page.add_init_script(_hide_cookie_banner_js)

    while True:
        try:
            response = await page.goto(url, wait_until='networkidle')
        except PlaywrightError:
            pass
        else:
            if response is None or response.status == 511:
                input('触发验证，等待手动将验证通过...')
                continue
            break

    return page


async def get_product_count_of_category(page: Page) -> int:
    """解析该类目总共有多少个产品"""
    count_strong = page.locator('css=div.control-label.js-listing-pagination').locator('xpath=/strong[2]')
    return int(await count_strong.inner_text())


async def newaddtocart_dialog_handler(button: Locator) -> None:
    """加购成功后的弹窗的处理器"""
    try:
        await button.click(timeout=0.1 * MS1000)
    except PlaywrightError:
        pass


async def parse_card_item(card: Locator, category: str, source_url: str, rank: int) -> ProductCardItem:
    """解析单个产品卡片的上的数据"""

    # 卡片截图的 Base64
    # card_screenshot_base64 = base64.b64encode(await card.screenshot(type='png', timeout=MS1000)).decode()

    # 解析产品名
    title = await card.locator('css=a.card-v2-title').inner_text(timeout=MS1000)

    # 解析 pnk
    data_url: str = await card.get_attribute('data-url', timeout=MS1000)  # type: ignore
    pnk: str = re.search(r'/pd/([A-Z0-9]{9})(/$)', data_url).group(1)  # type: ignore

    # 解析产品图链接
    image_url = None
    try:
        thumb_image_url = await card.locator('css=div.img-component > img[src]').get_attribute(
            'src', timeout=MS1000
        )
    except PlaywrightError:
        pass
    else:
        if thumb_image_url is not None:
            image_url = clean_product_image_url(thumb_image_url)

    # 解析 product_id data-offer-id
    data_offer_id: str = await card.get_attribute('data-offer-id', timeout=MS1000)  # type: ignore

    # 解析 Top 标
    top_favorite = (
        await card.locator(
            'css=span.card-v2-badge-cmp',
            has_text=re.compile(r'Top Favorite'),
        ).count()
        > 0
    )

    # 解析价格
    price_match: re.Match[str] = re.search(
        r'(\d+),(\d+) Lei', await card.locator('css=p.product-new-price').inner_text(timeout=MS1000)
    )  # type: ignore
    price = float(f'{price_match.group(1)}.{price_match.group(2)}')

    # 解析评分
    rating: Optional[float] = None
    rating_span = card.locator('css=span.average-rating')
    if await rating_span.count() == 1:
        rating = float(await rating_span.inner_text(timeout=MS1000))

    # 解析评论数
    review = 0
    review_span = card.locator('css=span.visible-xs-inline-block')
    if await review_span.count() == 1:
        review = int(re.search(r'\((\d+)\)', await review_span.inner_text(timeout=MS1000)).group(1))  # type: ignore

    return ProductCardItem(
        title=title,
        pnk=pnk,
        product_id=data_offer_id,
        category=category,
        source_url=source_url,
        rank_in_page=rank,
        top_favorite=top_favorite,
        price=price,
        rating=rating,
        review=review,
        image_url=image_url,
        # card_div_screenshot_base64=card_screenshot_base64,
        cart_added=False,
        max_qty=None,
    )


_success_added_products: dict[str, set[str]] = defaultdict(set)
"""加购成功的产品 { category: { product_ids } }"""
_newaddtocart_endpoint = re.compile(r'emag\.ro/newaddtocart')
"""加购请求的 endpoint"""


async def newaddtocart(card: Locator) -> None:
    """加购单个产品"""
    # BUG 不能保证所有点击了加购的产品确实已被加购
    # BUG 会重复加购

    while True:
        try:
            await card.locator('css=button.yeahIWantThisProduct').click(timeout=MS1000)
        except PlaywrightError:
            continue
        else:
            break


def _newaddtocart_request_handler(category: str, route: Route, logger: Logger) -> Awaitable[None]:
    """检查要加购的产品是否已经被加购过，已被加购就拦截该请求"""
    post_data = route.request.post_data

    if post_data is None:
        return route.continue_()
    product_id_match = re.search(r'product%5B%5D=(\d+)', post_data)
    if product_id_match is None:
        return route.continue_()

    # 如果产品已被加购就拒绝该加购请求
    product_id: str = product_id_match.group(1)
    if product_id in _success_added_products[category]:
        logger.warning(f'检测到已加购产品，data-offer-id={product_id} 的加购请求已拒绝')
        return route.abort()

    return route.continue_()


def _newaddtocart_response_handler(category: str, response: Response, logger: Logger) -> None:
    """将加购成功的产品的请求记录到 _success_added_products"""
    if response.status == 511:
        logger.error(f'请求 "{response.url}" 触发验证')
        input('等待处理验证后继续...')

    # 不是加购请求 newaddtocart
    if _newaddtocart_endpoint.search(response.url) is None:
        return

    # 请求体为空
    post_data = response.request.post_data

    if post_data is None:
        return
    product_id_match = re.search(r'product.*?=(\d+)', post_data)
    if product_id_match is None:
        return

    # 记录该产品已被加购
    product_id: str = product_id_match.group(1)
    _success_added_products[category].add(product_id)
    logger.debug(f'记录加购请求，添加 data-offer-id={product_id} 到已加购集合')


async def category_handler(page: Page, category: str, logger: Logger) -> list[ProductCardItem]:
    """
    处理一个类目页

    1. 加购前 40 个产品，并解析其产品卡片
    2. 打开购物车解析已加购产品的最大可加购数
    3. 清空购物车
    4. 加购剩余产品，并解析其产品卡片
    5. 打开购物车解析已加购产品的最大可加购数
    6. 清空购物车
    """

    logger.info(f'处理类目 "{category}" 链接 "{page.url}"')

    # TODO 如何保证在触发验证后能暂停，并在通过验证后从暂停点继续？

    # 拦截已加购产品的加购请求
    await page.route(
        _newaddtocart_endpoint,
        lambda r: _newaddtocart_request_handler(category, r, logger),
    )
    # 记录加购成功的产品
    page.on(
        'response',
        lambda r: _newaddtocart_response_handler(category, r, logger),
    )

    # 非 Promovat、非 Vezi Detalii 的加购按钮的所属产品卡片
    product_card_divs = page.locator(
        'div.card-item[data-offer-id]',
        has_not=page.locator('css=span.card-v2-badge-cmp.bg-light'),
        has=page.locator('css=button.yeahIWantThisProduct'),
    )

    result: list[ProductCardItem] = list()

    product_card_count = await product_card_divs.count()
    logger.debug(f'找到 {product_card_count} 个非 Promovat、非 Vezi Detalii 的产品卡片')

    # NOTICE 点击加购按钮的速度太快会导致页面崩溃
    # 处理加购弹窗
    await page.add_locator_handler(
        page.locator('css=div.modal-header > button.close'),
        newaddtocart_dialog_handler,
    )

    for i in range(product_card_count):
        # 每处理一个产品卡片就等待 0.5 秒
        await asyncio.sleep(0.5)

        # 加购到 40 个产品，处理一批
        if i == 40:
            logger.info('等待所有加购请求完成')
            await wait_for_networkidle(page, 10 * MS1000)

            _cart_page = await goto_cart_page(page.context, logger)
            await parse_max_qtys(_cart_page, result, logger)
            await clear_cart(_cart_page, logger)
            await _cart_page.close()

        logger.debug(f'尝试加购产品 #{i+1}')
        await newaddtocart(product_card_divs.nth(i))
        logger.debug(f'尝试解析产品 #{i+1}')
        p = await parse_card_item(
            product_card_divs.nth(i),
            category,
            page.url,
            i + 1,
        )
        logger.debug(f'解析产品成功 #{p.rank_in_page} pnk="{p.pnk}" data-offer-id={p.product_id}')
        result.append(p)

    logger.info('等待所有加购请求完成')
    await wait_for_networkidle(page, 10 * MS1000)

    _cart_page = await goto_cart_page(page.context, logger)
    await parse_max_qtys(_cart_page, result, logger)
    await clear_cart(_cart_page, logger)
    await _cart_page.close()

    await page.close()

    return result
