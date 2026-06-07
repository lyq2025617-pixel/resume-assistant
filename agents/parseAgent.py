"""Agent: 从 PDF 简历中提取文本"""
import io
import pdfplumber


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """从 PDF 字节数据中提取文本"""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
            return "\n\n".join(p for p in pages if p.strip())
    except Exception as e:
        raise ValueError(f"PDF 解析失败: {e}")
