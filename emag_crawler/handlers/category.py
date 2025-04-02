"""处理类目页"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from scraper_utils.constants.time_constant import MS1000
from scraper_utils.exceptions.browser_exception import PlaywrightError

from ..models.category import CardItemDO, CategoryPageDO
from ..utils import hide_cookie_banner

if TYPE_CHECKING:
    from typing import Optional

    from playwright.async_api import BrowserContext, Page, Locator

"""
用 goto 打开的类目页链接，产品数据是放在各个产品卡片里 css=div.card-standard。

点击 css=button.listing-view-type-change 的切换产品展示方式按钮后，
会发起 www.emag.ro/search-by-filters-with-redirect 的请求，并跳转至第 1 页，该请求的响应包含了第 1 页的产品数据。

点击底部的换页按钮后，会发起 www.emag.ro/search-by-url 的请求，该请求的响应包含了新页的产品数据。
"""

# TODO 怎么处理切换产品展示方式、点击换页按钮后触发的验证？

"""
async def goto_category_page(context: BrowserContext, url: str) -> Page: ...
async def change_listing_view_type(page: Page) -> Response: ...
async def goto_next_page(page: Page) -> Response: ...
"""


async def goto_category_page(context: BrowserContext, url: str) -> Page:
    """打开类目页"""
    page = await context.new_page()
    await hide_cookie_banner(page)
    while True:
        try:
            response = await page.goto(url, wait_until='networkidle')
        except PlaywrightError:
            pass
        else:
            if response is None or response.status == 511:
                input('触发验证，验证通过后按 Enter 继续...')
                continue
            break

    return page


async def parse_category_name(page: Page) -> str:
    """类目名称"""
    category_name_h1 = page.locator('css=h1.title-phrasing')
    category_name = await category_name_h1.inner_text(timeout=MS1000)
    return category_name


async def parse_category_product_count(page: Page) -> int:
    """该类目共有多少产品"""
    count_strong = page.locator('css=div.control-label.js-listing-pagination').locator('xpath=/strong[2]')
    return int(await count_strong.inner_text())


async def parse_category(page: Page) -> CategoryPageDO:
    """解析类目页的类目信息"""
    name = await parse_category_name(page)
    product_count = await parse_category_product_count(page)
    url_match = re.search(r'(https?://.*?/c)(\?|/|$)', page.url)
    url = '/'
    if url_match is not None:
        url = url_match.group(1)
        url = re.sub(r'/p\d+(?=/c)', '', url)
    return CategoryPageDO(name=name, url=url, product_count=product_count)


async def parse_page_number(page: Page) -> int:
    """解析当前页码"""
    data_page_a = page.locator(
        'css=ul.pagination > li.active > a[data-page]',
    )
    page_num = int(await data_page_a.inner_text(timeout=MS1000))
    return page_num


async def parse_card_item(card: Locator, rank: int, page_num: int, count_in_page: int) -> CardItemDO:
    """解析单个产品卡片"""

    # 从产品卡牌中解析类目
    category: str = await card.get_attribute('data-category-name', timeout=MS1000)  # type: ignore
    category_id: str = await card.get_attribute('data-category-id', timeout=MS1000)  # type: ignore

    # 从收藏按钮中解析产品数据
    add_to_favorites_button = card.locator('css=button.add-to-favorites[data-product]')
    data_product: str = await add_to_favorites_button.get_attribute('data-product', timeout=MS1000)  # type: ignore
    data_product_json = json.loads(data_product)
    pnk = str(data_product_json['pnk'])
    product_id = str(data_product_json['productid'])
    offer_id = str(data_product_json['offerid'])
    name = str(data_product_json['product_name'])
    price = float(data_product_json['price'])
    category_trail = str(data_product_json['category_trail'])

    # 有无 Top Favorite 标签
    top_favorite = (
        await card.locator(
            'css=span.card-v2-badge-cmp',
            has_text=re.compile(r'Top Favorite'),
        ).count()
        > 0
    )

    # 解析评分
    rating: Optional[float] = None
    rating_span = card.locator('css=span.average-rating')
    if await rating_span.count() == 1:
        rating = float(await rating_span.inner_text(timeout=MS1000))

    # 解析评论数
    review_count: Optional[int] = None
    review_span = card.locator('css=span.visible-xs-inline-block')
    if await review_span.count() == 1:
        review_match = re.search(r'\((\d+)\)', await review_span.inner_text(timeout=MS1000))
        if review_match is not None:
            review_count = int(review_match.group(1))

    return CardItemDO(
        pnk=pnk,
        name=name,
        category=category,
        category_trail=category_trail,
        category_id=category_id,
        product_id=product_id,
        offer_id=offer_id,
        price=price,
        top_favorite=top_favorite,
        rating=rating,
        review_count=review_count,
        rank_in_page=rank,
        page_num=page_num,
        count_in_page=count_in_page,
    )


async def parse_card_items(page: Page) -> list[CardItemDO]:
    """解析页面的所有产品卡片"""
    result: list[CardItemDO] = list()

    card_item_divs = page.locator(
        'css=div.card-standard[data-category-name][data-category-id]',
        has=page.locator('css=button.add-to-favorites[data-product]'),
        has_not=page.locator('css=span.card-v2-badge-cmp.bg-light'),
    )
    card_count = await card_item_divs.count()
    page_num = await parse_page_number(page)

    for i in range(card_count):
        result.append(
            await parse_card_item(
                card_item_divs.nth(i),
                i + 1,
                page_num,
                card_count,
            )
        )

    return result


async def goto_next_page(page: Page) -> None:
    """点击下一页按钮跳转至下一页"""
    # NOTICE 点击下一页按钮后会将当前页面导航至下一页
    # NOTICE 点击下一页按钮后会发起 search-by-url 的请求，该请求的响应包含了新一页的产品数据

    """
    TODO
    1. 检测有无下一页
    2. 点击并导航至下一页
    3. 导航过程中触发验证要怎么办？
    """
    next_page_a = page.locator('css=a.js-change-page[aria-label="Next"]')
    while True:
        try:
            async with page.expect_navigation(
                url=re.compile(r''),
                # wait_until='networkidle',
            ) as response_event:
                await next_page_a.click(timeout=MS1000)

        except PlaywrightError:
            continue
        else:
            response = await response_event.value
            if response.status == 511:
                input('触发验证，验证通过后按 Enter 继续...')
                continue
            break
