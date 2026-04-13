# LuminaPayroll

LuminaPayroll 自动化测试工程 - 基于PO模式

## 工程结构

```
LuminaPayroll/
├── config/              # 配置文件
│   ├── config.yaml     # 全局配置
│   └── environments/   # 环境配置 (dev/test/prod)
├── common/             # 公共模块
│   ├── base_api.py    # API基类
│   ├── base_page.py   # Page基类
│   ├── utils.py       # 工具函数
│   └── logger.py      # 日志配置
├── pages/              # 页面对象/接口对象
│   ├── api/           # API接口封装
│   └── ui/            # UI页面封装
├── testcases/          # 测试用例
│   ├── api/           # API测试用例
│   └── ui/            # UI测试用例
├── testdata/           # 测试数据
├── reports/            # 测试报告
│   ├── html/          # HTML报告
│   └── logs/          # 日志文件
├── conftest.py        # pytest配置
└── pytest.ini         # pytest配置
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装浏览器 (仅UI测试需要)

```bash
playwright install
```

### 3. 配置环境

编辑 `config/environments/dev.yaml` 修改测试环境地址。

设置环境变量:
```bash
export LUMINA_ENV=dev  # dev/test/prod
```

### 4. 运行测试

```bash
# 运行所有测试
pytest

# 运行API测试
pytest -m api

# 运行UI测试
pytest -m ui

# 运行工资模块测试
pytest -m payroll

# 生成HTML报告
pytest --html=reports/html/report.html

# 生成Allure报告
pytest --alluredir=reports/allure
allure serve reports/allure
```

## 添加新用例

### API测试用例

1. 在 `pages/api/` 下创建接口封装类
2. 在 `testcases/api/` 下创建测试用例

或使用自然语言生成:
```bash
python3 ~/.qoderwork/skills/lumina-payroll/scripts/generate_case.py \
  "POST /api/payroll/calculate 参数employeeId=123" \
  --page payroll \
  -o testcases/api/test_payroll_new.py
```

### UI测试用例

1. 在 `pages/ui/` 下创建页面对象类
2. 在 `testcases/ui/` 下创建测试用例

或使用自然语言生成:
```bash
python3 ~/.qoderwork/skills/lumina-payroll/scripts/generate_case.py \
  "打开工资页面 输入员工编号123 点击计算" \
  --type ui --page payroll \
  -o testcases/ui/test_payroll_new.py
```

## 自然语言用例格式

**API用例示例:**
```
POST /api/payroll/calculate 参数employeeId=123,month=2024-01
验证状态码200
验证返回data.totalAmount大于0
```

**UI用例示例:**
```
打开工资计算页面
输入员工编号123
选择月份2024-01
点击计算按钮
验证显示计算结果
```

## 生成测试报告

```bash
# 生成可视化HTML报告
python3 ~/.qoderwork/skills/lumina-payroll/scripts/generate_report.py --demo

# 从pytest结果生成
pytest --json-report --json-report-file=reports/result.json
python3 ~/.qoderwork/skills/lumina-payroll/scripts/generate_report.py reports/result.json
```

---

生成时间: 2026-04-13 20:32:47
