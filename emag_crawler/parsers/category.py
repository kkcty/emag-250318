"""解析类目页"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..logger import logger

if TYPE_CHECKING:
    from typing import Any


def parse_search_by_filters_with_redirect_response(response_json: Any):
    """解析 search-by-filters-with-redirect 请求的响应"""
    data: dict[str, Any] = response_json['data']
    # TODO


def parse_search_by_url_response(response_json: Any) -> dict[str, Any]:
    """解析 search-by-url 请求的响应"""
    data_dict: dict[str, Any] = response_json['data']

    ##### category #####
    category_dict: dict[str, Any] = data_dict['category']
    category_id = str(category_dict['id'])  # 类目 id
    category_name = str(category_dict['name'])  # 类目名
    category_trail = str(category_dict['trail'])  # 类目路径
    category_english_name = str(category_dict['english_name'])  # 类目的英文名

    ##### pagination #####
    pagination_dict: dict[str, Any] = data_dict['pagination']
    category_total_item_count = int(pagination_dict['items_count'])  # 整个类目的产品数
    page_per_page_item_count = int(pagination_dict['items_per_page'])  # 一页的产品数

    pages_list: list[dict[str, Any]] = pagination_dict['pages']
    page_current_page_number = next(
        (int(_['id']) for _ in pages_list if _['is_selected'] is True), None
    )  # 当前页码

    ##### base_url #####
    base_url_dict: dict[str, Any] = data_dict['base_url']
    category_base_url = f'{base_url_dict['desktop_base']}{base_url_dict['path']}'  # 类目第一页的链接

    ##### url #####
    url_dict: dict[str, Any] = data_dict['url']
    page_current_page_url = f'{url_dict['desktop_base']}{url_dict['path']}'  # 当前页的链接

    ##### items #####
    items_list: list[dict[str, Any]] = data_dict['items']
    items: list[dict[str, Any]] = list()
    for item_rank, item in enumerate(items_list, 1):
        item_id = str(item['id'])  # 产品 id
        item_name = str(item['name'])  # 产品名
        item_pnk = str(item['part_number_key'])  # 产品 PNK
        item_image_url = str(item['image']['original'])  # 产品图链接

        item_feedback_dict: dict[str, Any] = item['feedback']
        item_rating = float(item_feedback_dict['rating'])  # 产品评分
        item_reviews_count = int(item_feedback_dict['reviews']['count'])  # 产品评论数

        item_url_dict: dict[str, str] = item['url']
        item_url = str(f'{item_url_dict['desktop_base']}{item_url_dict['path']}')  # 产品详情页链接

        item_offer_dict: dict[str, Any] = item['offer']
        item_offer_id = str(item_offer_dict['id'])  # 产品 offer-id
        item_offer_price_dict: dict[str, Any] = item_offer_dict['price']
        # TODO offer-id、价格、Top Favorite 还没做

        items.append(
            {
                'rank': item_rank,
                'id': item_id,
                'name': item_name,
                'pnk': item_pnk,
                'image_url': item_image_url,
                'rating': item_rating,
                'reviews_count': item_reviews_count,
                'url': item_url,
            }
        )

    return {
        'id': category_id,
        'name': category_name,
        'trail': category_trail,
        'english_name': category_english_name,
        'base_url': category_base_url,
        'item_count_total': category_total_item_count,
        'item_count_per_page': page_per_page_item_count,
        'current_page_number': page_current_page_number,
        'current_page_url': page_current_page_url,
        'items': items,
    }
