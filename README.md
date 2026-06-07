# 简历自动更新助手

一个基于 AI 的简历定制与面试准备工具，供同学们免费使用。

## 功能

- **登录保护**：访问需密码，保护简历隐私
- **简历编辑**：可视化编辑个人信息、技能、实习经历（STAR 法则）、项目经历
- **PDF 导入**：上传已有 PDF 简历，自动提取文本
- **JD 定制**：粘贴目标岗位 JD，AI 根据 JD 自动优化简历内容，突出匹配关键词
- **面试问题**：基于简历和 JD 生成高概率面试问题，附带考察点说明
- **预览导出**：实时预览简历，浏览器直接打印导出 PDF

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（本地运行）

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
ANTHROPIC_API_KEY=sk-ant-你的真实密钥
ACCESS_PASSWORD=自定义访问密码
```

### 3. 启动服务

```bash
python app.py
```

浏览器访问：http://localhost:8000，输入密码后即可使用。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API 密钥（云端部署时配置） | 无 |
| `ANTHROPIC_BASE_URL` | 可选。API 基础 URL | `https://api.anthropic.com` |
| `ANTHROPIC_MODEL` | 可选。使用的模型名称 | `claude-sonnet-4-6` |
| `ACCESS_PASSWORD` | 访问密码 | `resume2025` |
| `SECRET_KEY` | Session 加密密钥 | 自动生成 |
| `PORT` | 可选。服务端口 | `8000` |

## 云端部署（Render 免费）

1. Fork 本仓库到你的 GitHub 账户
2. 打开 [Render](https://render.com)，登录 GitHub 账号
3. 点击 **New +** → **Web Service** → 选择 `resume-assistant` 仓库
4. 按 `render.yaml` 自动配置，手动填写以下环境变量：
   - `ANTHROPIC_API_KEY`：你的 API Key
   - `ACCESS_PASSWORD`：自定义访问密码
5. 点击 **Deploy**，等待部署完成
6. 访问 Render 分配的域名，输入密码即可使用

> **安全说明**：API Key 存储在 Render 环境变量中，不会暴露给前端或写入代码仓库。

## 技术栈

- **后端**：Python + FastAPI
- **AI**：Anthropic Claude API
- **前端**：HTML + JavaScript + TailwindCSS
- **PDF 解析**：pdfplumber
- **模板引擎**：Jinja2
- **Session**：Starlette SessionMiddleware

## 注意事项

- `resume_data.json` 已加入 `.gitignore`，不会被提交到仓库
- `.env` 已加入 `.gitignore`，**切勿将 API Key 提交到公开仓库**
- AI 生成的内容仅供参考，请仔细核对后再使用

## 开源协议

MIT
