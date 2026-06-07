"""
简历自动更新助手 - FastAPI Web 应用
功能：登录认证 → 编辑简历 → 上传 JD → AI 定制简历 → 生成面试问题 → 导出 PDF
部署：支持 Render 等云平台，API Key 通过环境变量配置（不暴露）
"""
import os
import json
import shutil
import time
import logging
import traceback
import anthropic
import hashlib
from pathlib import Path
from collections import defaultdict
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from agents.parseAgent import extract_text_from_pdf
from agents.structureAgent import parse_to_resume_data
from agents.optimizeAgent import optimize_resume
from agents.interviewAgent import generate_questions

# ---- 日志配置 ----
logger = logging.getLogger("resume-assistant")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)

app = FastAPI(title="简历自动更新助手")

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "resume_data.json"
EXAMPLE_FILE = BASE_DIR / "resume_data.example.json"

# ---- 安全配置 ----
# 登录密码：通过环境变量设置，默认 "resume2025"
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "resume2025")
# Session 加密密钥（Render 部署时设为环境变量）
SECRET_KEY = os.environ.get("SECRET_KEY", hashlib.sha256(b"resume-assistant-secret").hexdigest())

# ---- 限流配置 ----
RATE_LIMIT_MAX = int(os.environ.get("RATE_LIMIT_MAX", "30"))       # 每分钟最大请求数
RATE_LIMIT_WINDOW = 60  # 窗口（秒）
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

# 请求体大小限制（10 MB）
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))

# Setup static files and templates
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Create Jinja2 environment with no cache
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=select_autoescape(),
    cache_size=0,
)
templates = Jinja2Templates(env=jinja_env)

# Initialize Anthropic client (API Key 从环境变量读取，云端部署时配置)
_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

client = anthropic.Anthropic(
    api_key=_api_key or "dummy-key",
    base_url=_base_url,
)


def load_data():
    if not DATA_FILE.exists():
        if EXAMPLE_FILE.exists():
            shutil.copy(EXAMPLE_FILE, DATA_FILE)
        else:
            raise FileNotFoundError("找不到 resume_data.json 或 resume_data.example.json")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_auth(request: Request) -> bool:
    """检查用户是否已登录"""
    return request.session.get("authenticated", False)


def require_auth(request: Request):
    """验证登录状态，未登录则重定向到登录页"""
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    return None


def _get_client_ip(request: Request) -> str:
    """获取客户端 IP（考虑代理场景）"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("x-real-ip") or request.client.host


def _check_rate_limit(ip: str) -> bool:
    """
    滑动窗口限流：返回 True 表示允许，False 表示超限。
    仅对 /api/* 路径生效。
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    # 清理过期记录
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > window_start]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_store[ip].append(now)
    return True


# ---- 限流中间件 ----
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 仅限制 API 请求，跳过静态文件和页面
    if request.url.path.startswith("/api/"):
        ip = _get_client_ip(request)
        if not _check_rate_limit(ip):
            logger.warning("Rate limit exceeded for IP: %s", ip)
            return JSONResponse(
                status_code=429,
                content={"error": "请求过于频繁，请稍后重试"}
            )
    response = await call_next(request)
    return response


# ---- 请求体大小中间件 ----
@app.middleware("http")
async def max_size_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "请求体过大，请上传不超过 %d MB 的内容" % (MAX_UPLOAD_BYTES // (1024 * 1024))}
        )
    response = await call_next(request)
    return response


# ---- 登录/认证路由（无需认证） ----

LOGIN_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>登录 - 简历自动更新助手</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen flex items-center justify-center">
  <div class="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm">
    <div class="text-center mb-6">
      <div class="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold text-2xl mx-auto mb-3">简</div>
      <h1 class="text-xl font-bold text-gray-800">简历自动更新助手</h1>
      <p class="text-sm text-gray-500 mt-1">请输入访问密码</p>
    </div>
    <form method="POST" action="/login">
      <input type="password" name="password" placeholder="输入密码" required
        class="w-full px-4 py-3 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
      <button type="submit"
        class="w-full mt-4 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition">
        登录
      </button>
    </form>
    <p class="text-xs text-gray-400 text-center mt-4">忘记密码请联系管理员</p>
  </div>
</body>
</html>"""


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if check_auth(request):
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse(content=LOGIN_PAGE)


@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    # 密码比对（支持简单哈希比对，也支持明文比对）
    hashed_input = hashlib.sha256(password.encode()).hexdigest()
    stored = ACCESS_PASSWORD
    # 也尝试哈希比较存储的密码
    hashed_stored = hashlib.sha256(stored.encode()).hexdigest() if len(stored) < 128 else stored

    if password == stored or hashed_input == stored or hashed_input == hashed_stored:
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=302)
    return HTMLResponse(content=LOGIN_PAGE.replace(
        '<p class="text-xs text-gray-400 text-center mt-4">',
        '<p class="text-xs text-red-500 text-center mt-2">密码错误，请重试</p><p class="text-xs text-gray-400 text-center mt-4">'
    ))


@app.get("/logout")
async def logout(request: Request):
    request.session["authenticated"] = False
    return RedirectResponse(url="/login", status_code=302)


# ---- 受保护的路由 ----

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect
    data = load_data()
    return templates.TemplateResponse(request, "index.html", {"data": data})


@app.get("/api/data")
async def get_data(request: Request):
    auth_redirect = require_auth(request)
    if auth_redirect:
        return RedirectResponse(url="/login")
    return load_data()


class UpdateData(BaseModel):
    data: dict


@app.post("/api/data")
async def update_data(body: UpdateData, request: Request):
    auth_redirect = require_auth(request)
    if auth_redirect:
        return RedirectResponse(url="/login")
    save_data(body.data)
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_resume(request: Request, file: UploadFile = File(...)):
    auth_redirect = require_auth(request)
    if auth_redirect:
        return RedirectResponse(url="/login")
    if not file.filename.endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "仅支持 PDF 文件"})
    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": "文件过大"}
        )
    try:
        text = extract_text_from_pdf(pdf_bytes)
        return {"text": text, "filename": file.filename}
    except ValueError as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class ParseRequest(BaseModel):
    text: str


@app.post("/api/parse-to-data")
async def parse_to_data(body: ParseRequest, request: Request):
    """将 PDF 解析后的原始文本通过 AI 转换为结构化简历数据"""
    auth_redirect = require_auth(request)
    if auth_redirect:
        return RedirectResponse(url="/login")
    if not _api_key or _api_key == "dummy-key":
        return JSONResponse(
            status_code=503,
            content={"error": "服务配置中，AI 功能暂不可用"}
        )
    try:
        result = parse_to_resume_data(client, MODEL, body.text)
        return result
    except Exception as e:
        logger.exception("Parse to data endpoint error")
        return JSONResponse(status_code=500, content={"error": str(e)})


class JDRequest(BaseModel):
    jd_text: str


@app.post("/api/tailor")
async def tailor_resume(body: JDRequest, request: Request):
    auth_redirect = require_auth(request)
    if auth_redirect:
        return RedirectResponse(url="/login")
    if not _api_key or _api_key == "dummy-key":
        return JSONResponse(
            status_code=503,
            content={"error": "服务配置中，AI 功能暂不可用"}
        )
    try:
        data = load_data()
        result = optimize_resume(client, MODEL, data, body.jd_text)
        return result
    except Exception as e:
        logger.exception("Tailor endpoint error")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/analyze-jd")
async def analyze_jd(body: JDRequest, request: Request):
    """分析 JD 并返回结构化数据（关键词、经验要求、职责、匹配建议）"""
    auth_redirect = require_auth(request)
    if auth_redirect:
        return RedirectResponse(url="/login")
    if not _api_key or _api_key == "dummy-key":
        return JSONResponse(
            status_code=503,
            content={"error": "服务配置中，AI 功能暂不可用"}
        )
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system="""你是资深技术招聘顾问。请分析用户提供的岗位 JD（Job Description），
提取关键信息并以 JSON 格式返回。

输出格式：
{
  "keywords": ["技能关键词1", "技能关键词2", ...],
  "experience_required": "经验要求描述（如：3-5年后端开发经验）",
  "key_responsibilities": ["职责1", "职责2", ...],
  "match_tips": ["匹配建议1", "匹配建议2", ...]
}

只输出 JSON，不要其他内容。""",
            messages=[{"role": "user", "content": body.jd_text}],
            temperature=0.3,
        )
        result = msg.content[0].text
        start = result.index("{")
        end = result.rindex("}") + 1
        return json.loads(result[start:end])
    except Exception as e:
        logger.exception("Analyze JD endpoint error")
        return JSONResponse(status_code=500, content={"error": str(e)})


class QuestionRequest(BaseModel):
    jd_text: str


@app.post("/api/questions")
async def generate_questions_route(body: QuestionRequest, request: Request):
    auth_redirect = require_auth(request)
    if auth_redirect:
        return RedirectResponse(url="/login")
    if not _api_key or _api_key == "dummy-key":
        return JSONResponse(
            status_code=503,
            content={"error": "服务配置中，AI 功能暂不可用"}
        )
    try:
        data = load_data()
        questions = generate_questions(client, MODEL, data, body.jd_text)
        return {"questions": questions}
    except Exception as e:
        logger.exception("Questions endpoint error")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/preview", response_class=HTMLResponse)
async def preview_resume(request: Request):
    auth_redirect = require_auth(request)
    if auth_redirect:
        return auth_redirect
    data = load_data()
    return templates.TemplateResponse(request, "resume_print.html", {"data": data})


# ---- 全局异常处理器 ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常，返回标准 JSON 错误响应"""
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url.path, tb)
    return JSONResponse(
        status_code=500,
        content={
            "error": "服务器内部错误",
            "detail": str(exc),
        },
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
