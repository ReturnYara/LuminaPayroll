import os
import yaml
from pathlib import Path
from playwright.sync_api import Page, expect
from typing import Optional
import logging


class BasePage:
    """LuminaPayroll UI页面基类"""

    def __init__(self, page: Page):
        self.page = page
        self.url = ""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载配置
        env = os.getenv("LUMINA_ENV", "dev")
        config_path = Path(__file__).parent.parent / "config" / "environments" / f"{env}.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.base_url = self.config.get("ui_base_url", "http://localhost:8080")

    def navigate(self, url: Optional[str] = None):
        """导航到页面，相对路径自动拼接 base_url"""
        target_url = url or self.url
        # 如果是相对路径（以 / 开头但不含 ://），拼接 base_url
        if target_url and not "://" in target_url:
            target_url = f"{self.base_url.rstrip('/')}{target_url}"
        self.logger.info(f"Navigating to: {target_url}")
        self.page.goto(target_url)

    def click(self, selector: str):
        """点击元素"""
        self.logger.info(f"Clicking: {selector}")
        self.page.click(selector)

    def fill(self, selector: str, value: str):
        """填写输入框"""
        self.logger.info(f"Filling {selector} with: {value}")
        self.page.fill(selector, value)

    def get_text(self, selector: str) -> str:
        """获取元素文本"""
        return self.page.inner_text(selector)

    def wait_for_selector(self, selector: str, timeout: int = 10000):
        """等待元素出现"""
        self.page.wait_for_selector(selector, timeout=timeout)

    def assert_element_visible(self, selector: str):
        """断言元素可见"""
        expect(self.page.locator(selector)).to_be_visible()

    def assert_url_contains(self, text: str):
        """断言URL包含文本"""
        expect(self.page).to_have_url(lambda url: text in url)

    def assert_text_contains(self, selector: str, text: str):
        """断言元素文本包含指定内容"""
        expect(self.page.locator(selector)).to_contain_text(text)
