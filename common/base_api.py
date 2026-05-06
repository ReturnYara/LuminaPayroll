import os
import requests
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class BaseApi:
    """LuminaPayroll API测试基类"""

    def __init__(self):
        self.config = self._load_config()
        self.base_url = self.config.get("api_base_url", "https://c4.yonyoucloud.com")
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_config(self) -> Dict[str, Any]:
        """加载环境配置"""
        env = os.getenv("LUMINA_ENV", "dev")
        config_path = Path(__file__).parent.parent / "config" / "environments" / f"{env}.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        headers.update(self.headers)

        self.logger.info(f"{method.upper()} {url}")

        response = self.session.request(
            method=method.upper(),
            url=url,
            headers=headers,
            **kwargs
        )

        self.logger.info(f"Response: {response.status_code}")
        return response

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        return self.request("DELETE", endpoint, **kwargs)
