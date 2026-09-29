"""pytest 共享配置：站点地址、代理、每个用例的起点页面。

对应 JS 端的 playwright.config.js：
  - BASE_URL     ←→  use.baseURL
  - proxy fixture ←→  use.proxy（读 HTTP(S)_PROXY 环境变量）
  - todo_page     ←→  test.beforeEach 里的 page.goto('./')
"""

import os

import pytest
from playwright.sync_api import Page

# 注意结尾的斜杠：站点部署在 /todomvc/ 子路径下，少了斜杠会 404
BASE_URL = "https://demo.playwright.dev/todomvc/"


def _proxy_server() -> str | None:
    """按 JS 端同样的顺序读代理：四个大小写变体都认。"""
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        value = os.environ.get(key)
        if value:
            return value
    return None


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """把 HTTP(S)_PROXY 注入到 browser.new_context()。

    pytest-playwright 自带这个 fixture，覆盖它就能改所有 context 的创建参数。
    playwright-python 没有「读环境变量自动走代理」的行为，必须显式传 proxy。
    """
    server = _proxy_server()
    if not server:
        return browser_context_args
    return {**browser_context_args, "proxy": {"server": server}}


@pytest.fixture
def todo_page(page: Page) -> Page:
    """每个用例的起点：打开 TodoMVC 首页，替代 JS 端的 test.beforeEach。

    这里用绝对 BASE_URL 而不是 page.goto('./')：相对路径要靠 new_context() 上的
    base_url 才能解析，多一层隐式依赖；常量写在这里，全项目只有一处定义站点地址。
    """
    page.goto(BASE_URL)
    return page
