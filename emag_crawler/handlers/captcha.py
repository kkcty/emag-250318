"""验证处理"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Response


def check_response_captcha(context: BrowserContext, response: Response) -> None:
    """如果响应触发了验证，就为 context 附加 captcha_flag = True"""
    if response.status == 511:
        context.captcha_flag = True  # type: ignore
    else:
        context.captcha_flag = False  # type: ignore
