"""类目页的数据模型"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, computed_field

if TYPE_CHECKING:
    pass


class CategoryPageDO(BaseModel):
    """类目页信息"""

    name: str = Field(..., description='类目名')
    # sef_name: str = Field(..., description='类目链接中的类目名')
    url: str = Field(..., description='类目链接')

    # div.control-label.js-listing-pagination
    product_count: int = Field(..., gt=0, description='产品总数')


class CardItemDO(BaseModel):
    """单个产品卡片的信息"""

    # div.card-standard

    pnk: str = Field(..., description='pnk')
    name: str = Field(..., description='listing')
    category: str = Field(..., description='类目')
    category_trail: str = Field(..., description='类目路径')
    category_id: str = Field(..., description='data-category-id')
    product_id: str = Field(..., description='data-product-id')
    offer_id: str = Field(..., description='data-offer-id')
    price: float = Field(..., gt=0, description='价格')
    rating: Optional[float] = Field(..., ge=0.0, description='评分')
    review_count: Optional[int] = Field(..., ge=0, description='评论数')
    top_favorite: bool = Field(False, description='Top Favorite 标志')
    rank_in_page: int = Field(..., ge=1, description='在本页的排名')
    count_in_page: int = Field(..., ge=1, description='该类目页的产品数')
    page_num: int = Field(..., ge=1, description='在类目页的页码')

    @computed_field(description='详情页链接')
    @property
    def url(self) -> str:
        """详情页链接"""
        return f'https://www.emag.ro/-/pd/{self.pnk}'

    @computed_field(description='在本类目的排名')
    @property
    def rank_in_category(self) -> int:
        """在本类目的排名"""
        return (self.page_num - 1) * self.count_in_page + self.rank_in_page
