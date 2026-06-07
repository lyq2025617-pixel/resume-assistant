"""
简历自动更新助手 - FastAPI Web 应用
功能：编辑简历 → 上传 JD → AI 定制简历 → 生成面试问题 → 浏览器打印导出 PDF
开源版：供同学们免费使用
"""
import os
import json
import shutil
import anthropic
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from agents.parseAgent import extract_text_from_pdf
from agents.optimizeAgent import optimize_resume
from agents.interviewAgent import generate_questions

app = FastAPI(title="简历自动更新助手")

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "resume_data.json"
EXAMPLE_FILE = BASE_DIR / "resume_data.example.json"

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

# Create Jinja2 environment with no cache
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=select_autoescape(),
    cache_size=0,
)
templates = Jinja2Templates(env=jinja_env)

# Initialize Anthropic client
_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not _api_key or _api_key == "your-api-key-here":
    print("\n" + "=" * 60)
    print("⚠️  警告：未设置 ANTHROPIC_API_KEY")
    print("请复制 .env.example 为 .env 并填入你的 API Key")
    print("获取 API Key: https://console.anthropic.com/")
    print("=" * 60 + "\n")

client = anthropic.Anthropic(
    api_key=_api_key or "dummy-key",
    base_url=os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
)
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def load_data():
    if not DATA_FILE.exists():
        if EXAMPLE_FILE.exists():
            shutil.copy(EXAMPLE_FILE, DATA_FILE)
            print(f"[提示] 已从示例数据创建 resume_data.json，请编辑为你的真实信息")
        else:
            raise FileNotFoundError("找不到 resume_data.json 或 resume_data.example.json")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_api_key():
    """检查 API Key 是否配置"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or key == "your-api-key-here":
        return False
    return True


# ---- Routes ----

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = load_data()
    return templates.TemplateResponse(request, "index.html", {"data": data})


@app.get("/api/data")
async def get_data():
    return load_data()


class UpdateData(BaseModel):
    data: dict


@app.post("/api/data")
async def update_data(body: UpdateData):
    save_data(body.data)
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_resume(file: UploadFile = File(...)):
    """上传 PDF 简历文件，提取文本返回"""
    if not file.filename.endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "仅支持 PDF 文件"})
    pdf_bytes = await file.read()
    try:
        text = extract_text_from_pdf(pdf_bytes)
        return {"text": text, "filename": file.filename}
    except ValueError as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class JDRequest(BaseModel):
    jd_text: str


@app.post("/api/tailor")
async def tailor_resume(body: JDRequest):
    """根据 JD 定制简历内容"""
    if not check_api_key():
        return JSONResponse(
            status_code=401,
            content={"error": "未配置 API Key，请设置 ANTHROPIC_API_KEY 环境变量"}
        )
    try:
        data = load_data()
        result = optimize_resume(client, MODEL, data, body.jd_text)
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class QuestionRequest(BaseModel):
    jd_text: str


@app.post("/api/questions")
async def generate_questions_route(body: QuestionRequest):
    """根据 JD 生成面试问题"""
    if not check_api_key():
        return JSONResponse(
            status_code=401,
            content={"error": "未配置 API Key，请设置 ANTHROPIC_API_KEY 环境变量"}
        )
    try:
        data = load_data()
        questions = generate_questions(client, MODEL, data, body.jd_text)
        return {"questions": questions}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/preview", response_class=HTMLResponse)
async def preview_resume(request: Request):
    """预览简历（用于浏览器打印导出 PDF）"""
    data = load_data()
    return templates.TemplateResponse(request, "resume_print.html", {"data": data})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
