"""爬取行布局的类目页"""

import asyncio
import re

from playwright.async_api import async_playwright

from emag_crawler.handlers.category_page import _hide_cookie_banner_js


async def main():
    async with async_playwright() as pwr:
        browser = await pwr.chromium.connect_over_cdp('http://192.168.110.8/cdp/', timeout=1000)
        context = await browser.new_context(no_viewport=True)
        context.set_default_navigation_timeout(0)

        page = await context.new_page()
        await page.add_init_script(_hide_cookie_banner_js)
        # await page.goto('https://www.emag.ro/trotinete/c')
        await page.goto('https://www.emag.ro/jocuri-societate/c')

        # layout_buttons = page.locator('css=button.listing-view-type-change')
        # await layout_buttons.highlight()

        row_layout_button = page.locator('css=button.listing-view-type-change[data-type="1"]')
        # await row_layout_button.highlight()

        async with page.expect_response(
            re.compile(r'emag\.ro/search-by-filters-with-redirect')
        ) as response_event:
            await row_layout_button.click()
        response = await response_event.value

        json_data = await response.json()
        for i, v in enumerate(json_data['data']['items'], 1):
            print(i, v['part_number_key'])

        input('Enter...')


if __name__ == '__main__':
    asyncio.run(main())
