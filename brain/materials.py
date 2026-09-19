"""资料文本提取。C 负责。只处理能提取出文本的文件，不做图片和扫描件识别。"""
from __future__ import annotations
import io

MAX_CHARS = 30000      # 单场资料总量上限，超出部分先截断；TODO(C)：改成让 LLM 压缩成摘要


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(f"[第{i + 1}页]\n{page.extract_text() or ''}" for i, page in enumerate(reader.pages)).strip()
    if name.endswith(".docx"):
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs).strip()
    if name.endswith((".md", ".txt", ".csv", ".json")):
        return data.decode("utf-8", errors="replace").strip()
    raise ValueError(f"不支持的文件类型：{filename}。请改为粘贴文本。")
