"""测试"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from scraper_utils.utils.json_util import write_json_async

from emag_crawler.handlers.category import goto_pagination
from emag_crawler.parsers.category import parse_search_by_url_response
from emag_crawler.utils import connect_cdp
from emag_crawler.worker.category import start_crawler


if TYPE_CHECKING:
    pass


async def main():
    async with connect_cdp() as browser:

        # # 首页
        # page = await goto_category_page(context, 'https://www.emag.ro/seturi-constructie/c', logger)
        # # 中间页
        # page = await goto_category_page(context, 'https://www.emag.ro/seturi-constructie/p5/c')
        # # 末页
        # page = await goto_category_page(context, 'https://www.emag.ro/sisteme-teleconferinta/p4/c', logger)
        # # 首页+末页
        # page = await goto_category_page(
        #     context, 'https://www.emag.ro/memorie-externa-telefon-mobil/c', logger
        # )

        await start_crawler(browser, 'https://www.emag.ro/seturi-constructie/c')

        input('...')


if __name__ == '__main__':
    asyncio.run(main())
