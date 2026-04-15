import requests
from typing import Dict, Optional


class YonyouCloudApi:
    """用友云 API 封装
    
    基于 Charles 抓包分析实现：
    1. SSO 登录（ticket 方式）
    2. 切换租户
    """
    
    def __init__(self):
        self.base_url = "https://c4.yonyoucloud.com"
        self.session = requests.Session()
        self.headers = {
            "Host": "c4.yonyoucloud.com",
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "macOS",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9",
            "priority": "u=0, i"
        }
    
    def login_with_ticket(self, ticket: str, finger: str = "4fb3fa92d40c37c60c435e5b4d205890") -> requests.Response:
        """
        SSO 登录 - 使用 ticket
        
        Args:
            ticket: SSO ticket，如 "ST-689644639-s67Jr3XP3P2ndkjVp5M3-online"
            finger: 设备指纹
            
        Returns:
            Response 对象
        """
        url = f"{self.base_url}/login_light"
        params = {
            "yhtdesturl": "/yhtssoislogin",
            "finger": finger,
            "yhtrealservice": "https://c4.yonyoucloud.com",
            "ticket": ticket
        }
        
        headers = {
            **self.headers,
            "referer": "https://euc.yonyoucloud.com/",
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "navigate",
            "sec-fetch-dest": "iframe"
        }
        
        # 临时禁用 SSL 验证用于测试（生产环境应启用）
        response = self.session.get(url, params=params, headers=headers, allow_redirects=True, verify=False)
        print(f"[登录] Status: {response.status_code}")
        print(f"[登录] Cookies: {dict(self.session.cookies)}")
        return response
    
    def switch_tenant(self, tenant_id: str, dimension: Optional[str] = None, 
                     finger: str = "4fb3fa92d40c37c60c435e5b4d205890") -> requests.Response:
        """
        切换租户
        
        Args:
            tenant_id: 租户ID，如 "ppycw2h8"
            dimension: 维度，默认使用 tenant_id
            finger: 设备指纹
            
        Returns:
            Response 对象
        """
        if dimension is None:
            dimension = tenant_id
            
        url = f"{self.base_url}/"
        params = {
            "tenantId": tenant_id,
            "dimension": dimension,
            "switch": "true",
            "finger": finger
        }
        
        headers = {
            **self.headers,
            "referer": "https://c4.yonyoucloud.com/",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "sec-fetch-dest": "document"
        }
        
        # 临时禁用 SSL 验证用于测试（生产环境应启用）
        response = self.session.get(url, params=params, headers=headers, allow_redirects=True, verify=False)
        print(f"[切换租户] Status: {response.status_code}")
        print(f"[切换租户] URL: {response.url}")
        return response
    
    def get_current_tenant(self) -> str:
        """获取当前租户ID"""
        cookies = dict(self.session.cookies)
        return cookies.get("tenantid", "")
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        cookies = dict(self.session.cookies)
        # 检查关键 cookie 是否存在
        return "at" in cookies or "yht_access_token" in cookies


class YonyouAuthHelper:
    """用友云认证辅助类"""
    
    @staticmethod
    def extract_ticket_from_url(url: str) -> Optional[str]:
        """从 URL 中提取 ticket"""
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        return params.get("ticket", [None])[0]
    
    @staticmethod
    def parse_cookies(cookie_string: str) -> Dict[str, str]:
        """解析 cookie 字符串"""
        cookies = {}
        for item in cookie_string.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                cookies[key] = value
        return cookies
