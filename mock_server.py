#!/usr/bin/env python3
"""
LuminaPayroll Mock 服务器
用于演示登录测试
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time


class MockAuthHandler(BaseHTTPRequestHandler):
    """模拟认证接口"""
    
    def log_message(self, format, *args):
        """禁用默认日志"""
        pass
    
    def do_POST(self):
        """处理POST请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}
        
        # 登录接口
        if self.path == "/api/auth/login":
            self._handle_login(data)
        # 登出接口
        elif self.path == "/api/auth/logout":
            self._handle_logout(data)
        # 薪资计算接口
        elif self.path == "/api/payroll/calculate":
            self._handle_payroll_calculate(data)
        else:
            self._send_error(404, "Not Found")
    
    def do_GET(self):
        """处理GET请求"""
        if self.path.startswith("/api/payroll/"):
            self._handle_payroll()
        else:
            self._send_error(404, "Not Found")
    
    def _handle_login(self, data):
        """处理登录"""
        username = data.get("username", "")
        password = data.get("password", "")
        
        # 模拟账号验证
        valid_accounts = {
            "admin": "admin123",
            "user001": "user123"
        }
        
        if username in valid_accounts and valid_accounts[username] == password:
            # 设置session cookie
            session_id = f"session_{username}_{int(time.time())}"
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Set-Cookie', f'sessionid={session_id}; Path=/; HttpOnly')
            self.send_header('Set-Cookie', f'username={username}; Path=/')
            self.end_headers()
            
            response = {
                "code": 0,
                "message": "登录成功",
                "data": {
                    "token": f"mock_token_{username}_{int(time.time())}",
                    "username": username,
                    "role": "admin" if username == "admin" else "user"
                }
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            response = {
                "code": 1001,
                "message": "用户名或密码错误"
            }
            self._send_json(401, response)
    
    def _handle_logout(self, data):
        """处理登出"""
        response = {
            "code": 0,
            "message": "登出成功"
        }
        self._send_json(200, response)
    
    def _handle_payroll_calculate(self, data):
        """处理薪资计算"""
        # 获取cookie验证登录状态
        cookie_header = self.headers.get('Cookie', '')
        
        # 简单的cookie验证
        if 'sessionid=' not in cookie_header:
            response = {
                "code": 1002,
                "message": "未登录或登录已过期"
            }
            self._send_json(401, response)
            return
        
        # 计算薪资
        base_salary = data.get('baseSalary', 0)
        bonus = data.get('bonus', 0)
        total = base_salary + bonus
        
        response = {
            "code": 0,
            "message": "计算成功",
            "data": {
                "employeeId": data.get('employeeId'),
                "month": data.get('month'),
                "totalAmount": total,
                "baseSalary": base_salary,
                "bonus": bonus
            }
        }
        self._send_json(200, response)
    
    def _handle_payroll(self):
        """处理工资查询"""
        # 获取cookie验证登录状态
        cookie_header = self.headers.get('Cookie', '')
        
        # 简单的cookie验证
        if 'sessionid=' not in cookie_header:
            response = {
                "code": 1002,
                "message": "未登录或登录已过期"
            }
            self._send_json(401, response)
            return
        
        # 历史记录
        response = {
            "code": 0,
            "message": "成功",
            "data": [
                {
                    "month": "2024-01",
                    "totalAmount": 12000
                }
            ]
        }
        self._send_json(200, response)
    
    def _send_json(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error(self, status_code, message):
        """发送错误响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())


def start_mock_server(port=8080):
    """启动Mock服务器"""
    server = HTTPServer(('localhost', port), MockAuthHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    print(f"✅ Mock服务器已启动: http://localhost:{port}")
    return server


if __name__ == "__main__":
    server = start_mock_server()
    print("按 Ctrl+C 停止服务器")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止服务器...")
        server.shutdown()
