# Cursor 使用指南 - LuminaPayroll

## 🎯 快速开始

### 1. 在 Cursor 中打开工程
工程已自动打开，文件树在左侧显示。

### 2. 使用 AI 聊天（快捷键 `Cmd+L`）

#### 生成测试用例
在 AI 聊天框中输入：
```
生成测试用例：POST /api/payroll/calculate 参数employeeId=123,month=2024-01
```

#### 解释代码
选中代码后按 `Cmd+K`，输入：
```
解释这段代码的作用
```

#### 修复错误
选中错误代码后按 `Cmd+K`，输入：
```
修复这个错误
```

### 3. 使用 Tab 自动补全
Cursor 会根据上下文智能补全代码，按 `Tab` 接受建议。

## 📝 常用操作

### 运行测试
在终端（`Cmd+J`）中运行：
```bash
# 运行所有测试
pytest testcases/ -v

# 运行API测试
pytest testcases/api/ -v

# 运行UI测试
pytest testcases/ui/ -v

# 生成报告
pytest --html=reports/html/report.html
```

### 自然语言生成代码
在任意文件中，选中空白处按 `Cmd+K`，输入自然语言描述，Cursor 会生成代码。

示例：
```
添加一个测试工资历史查询的用例，需要验证返回的数据包含员工ID和工资月份
```

## 🔧 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Cmd+L` | 打开 AI 聊天 |
| `Cmd+K` | 内联编辑/生成 |
| `Tab` | 接受自动补全 |
| `Cmd+J` | 打开终端 |
| `Cmd+P` | 快速打开文件 |
| `Cmd+Shift+F` | 全局搜索 |
| `Cmd+Shift+L` | 选中所有匹配 |

## 📁 工程结构速览

```
LuminaPayroll/
├── pages/          # Page Object 封装
│   ├── api/        # API 接口封装
│   └── ui/         # UI 页面对象
├── testcases/      # 测试用例
│   ├── api/        # API 测试
│   └── ui/         # UI 测试
├── config/         # 配置文件
└── reports/        # 测试报告
```

## 💡 AI 提示技巧

### 1. 生成 API 测试
```
生成API测试：
- 接口：GET /api/payroll/history
- 参数：employeeId, month
- 断言：状态码200，返回列表不为空
```

### 2. 生成 UI 测试
```
生成UI测试：
- 页面：工资计算页
- 操作：输入员工编号、选择月份、点击计算
- 断言：显示计算结果
```

### 3. 重构代码
```
将这个测试函数重构为参数化测试，支持多组数据
```

### 4. 添加注释
```
为这段代码添加详细的 docstring 和注释
```

## 🐛 调试技巧

1. **设置断点**：点击行号左侧空白处
2. **启动调试**：按 `F5` 或点击左侧调试图标
3. **查看变量**：调试时鼠标悬停在变量上

## 📚 推荐阅读

- `SKILL.md` - 技能文档
- `EXAMPLES.md` - 使用示例
- `README.md` - 工程说明

---

**开始使用**：打开任意测试文件，按 `Cmd+L` 开始与 AI 对话！
