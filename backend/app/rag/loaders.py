"""文档加载器（单一职责：只负责把各类文件解析成纯文本）。

支持 .txt/.md/.pdf/.docx/.html。docx 走 zipfile 直读，避免额外依赖。

作者: 晨星
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

from app.core.errors import BadRequestError, NotFoundError

SUPPORTED = {".txt", ".md", ".markdown", ".pdf", ".docx", ".html", ".htm"}
MAX_BYTES = 20 * 1024 * 1024


def _read_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _read_docx(path: Path) -> str:
    """不依赖 python-docx：直接解压读取 word/document.xml。"""
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return re.sub(r"\n{3,}", "\n\n", xml).strip()


def _read_html(path: Path) -> str:
    raw = _read_plain(path)
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


_READERS = {
    ".txt": _read_plain,
    ".md": _read_plain,
    ".markdown": _read_plain,
    ".pdf": _read_pdf,
    ".docx": _read_docx,
    ".html": _read_html,
    ".htm": _read_html,
}


def load_text(path: str | Path) -> str:
    """按扩展名选择解析器，返回纯文本。"""
    p = Path(path)
    if not p.exists():
        raise NotFoundError(f"文件不存在: {p}")
    if p.stat().st_size > MAX_BYTES:
        raise BadRequestError(f"文件过大（>20MB）: {p.name}")
    suffix = p.suffix.lower()
    if suffix not in _READERS:
        raise BadRequestError(
            f"不支持的文件类型: {suffix}，支持 {', '.join(sorted(SUPPORTED))}"
        )
    text = _READERS[suffix](p)
    if not text.strip():
        raise BadRequestError(f"文件内容为空或无法提取文本: {p.name}")
    return text
