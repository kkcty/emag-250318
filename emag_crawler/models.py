"""数据模型"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, computed_field
from scraper_utils.utils.emag_util import build_product_url

if TYPE_CHECKING:
    pass


class ProductCardItem(BaseModel):
    """类目页的产品卡片所包含的产品数据"""

    title: str = Field(..., description='产品名')
    pnk: str = Field(..., description='产品编号')
    product_id: str = Field(..., description='类目页和详情页的 data-offer-id、购物车页的 data-id')
    category: str = Field(..., description='产品类目')
    source_url: str = Field(..., description='来源链接')
    rank_in_page: int = Field(..., ge=1, description='在来源链接的排行')
    top_favorite: bool = Field(False, description='是否带 Top Favorite 标志')
    price: Optional[float] = Field(None, gt=0.0, description='价格')
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description='评分')
    review: int = Field(..., ge=0, description='评论数')
    image_url: Optional[str] = Field(None, description='产品图原图链接')

    cart_added: bool = Field(False, description='是否已加购')
    max_qty: Optional[int] = Field(None, gt=0, description='最大可加购数')

    @computed_field
    @property
    def page_num(self) -> int:
        """页码"""
        m = re.search(r'/p(\d+)/c', self.source_url)
        if m is None:
            return 1
        return int(m.group(1))

    @computed_field
    @property
    def rank_in_category(self) -> int:
        """在这个类目内的排行"""
        return (self.page_num - 1) * 60 + self.rank_in_page

    @computed_field
    @property
    def detail_url(self) -> str:
        """详情页链接"""
        return build_product_url(self.pnk)
