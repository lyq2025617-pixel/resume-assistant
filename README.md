# 简历自动更新助手

一个基于 AI 的简历定制与面试准备工具，供同学们免费使用。

## 功能

- **简历编辑**：可视化编辑个人信息、技能、实习经历（STAR 法则）、项目经历
- **PDF 导入**：上传已有 PDF 简历，AI 自动提取文本
- **JD 定制**：粘贴目标岗位 JD，AI 根据 JD 自动优化简历内容，突出匹配关键词
- **面试问题**：基于简历和 JD 生成高概率面试问题，附带考察点说明
- **预览导出**：实时预览简历，浏览器直接打印导出 PDF

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量模板并填入你的 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入 [Anthropic API Key](https://console.anthropic.com/)：

```env
ANTHROPIC_API_KEY=sk-ant-你的真实密钥
```

> 你也可以使用兼容 Anthropic API 的代理服务，修改 `ANTHROPIC_BASE_URL` 即可。

### 3. 初始化简历数据

首次启动时，程序会自动从 `resume_data.example.json` 创建 `resume_data.json`。请编辑为你的真实信息。

### 4. 启动服务

```bash
python app.py
```

浏览器访问：http://localhost:8000

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | **必填**。Anthropic API 密钥 | 无 |
| `ANTHROPIC_BASE_URL` | 可选。API 基础 URL（代理地址） | `https://api.anthropic.com` |
| `ANTHROPIC_MODEL` | 可选。使用的模型名称 | `claude-sonnet-4-6` |
| `PORT` | 可选。服务端口 | `8000` |

## 技术栈

- **后端**：Python + FastAPI
- **AI**：Anthropic Claude API
- **前端**：HTML + JavaScript + TailwindCSS
- **PDF 解析**：pdfplumber
- **模板引擎**：Jinja2

## 注意事项

- `resume_data.json` 已加入 `.gitignore`，不会被提交到仓库
- `.env` 已加入 `.gitignore`，**切勿将 API Key 提交到公开仓库**
- AI 生成的内容仅供参考，请仔细核对后再使用

## 开源协议

MIT
