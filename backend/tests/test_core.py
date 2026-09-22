"""核心层与文本处理测试：配置 / 分块 / 加载器。

作者: 晨星
"""
from __future__ import annotations

import zipfile

import pytest

from app.core.config import Settings, reset_settings
from app.core.errors import BadRequestError, NotFoundError
from app.rag import chunker, loaders


# ---------------- 配置 ----------------
def test_settings_defaults_and_env_override(monkeypatch):
    monkeypatch.setenv("NEXUS_PORT", "9999")
    monkeypatch.setenv("NEXUS_TOP_K", "7")
    reset_settings()
    s = Settings.from_env()
    assert s.port == 9999
    assert s.top_k == 7
    reset_settings()


def test_settings_ensure_dirs(tmp_path):
    s = Settings()
    s.data_dir = tmp_path / "n" / "d"
    s.ensure_dirs()
    assert (s.data_dir / "index").exists()
    assert (s.data_dir / "memory").exists()


# ---------------- 分块 ----------------
def test_chunk_text_respects_size():
    text = "模块化设计。单一职责。接口清晰。" * 40
    chunks = chunker.chunk_text(text, chunk_size=120, overlap=20)
    assert chunks, "不应为空"
    assert all(len(c) <= 120 + 40 for c in chunks), "块长度应受控"
    assert "".join(chunks[:1]).startswith("模块化设计")


def test_chunk_text_empty_and_short():
    assert chunker.chunk_text("", 100, 10) == []
    assert chunker.chunk_text("短文本", 100, 10) == ["短文本"]


def test_chunk_overlap_applied():
    text = "A" * 300
    chunks = chunker.chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert chunks[1][:20] == chunks[0][-20:]


# ---------------- 加载器 ----------------
def test_load_text_plain_and_html(tmp_path):
    (tmp_path / "a.txt").write_text("hello nexus", encoding="utf-8")
    assert "hello nexus" in loaders.load_text(tmp_path / "a.txt")

    (tmp_path / "b.html").write_text(
        "<html><body><script>x</script><p>正文内容</p></body></html>",
        encoding="utf-8",
    )
    out = loaders.load_text(tmp_path / "b.html")
    assert "正文内容" in out and "x" not in out


def test_load_docx_without_extra_dependency(tmp_path):
    docx = tmp_path / "c.docx"
    xml = (
        '<?xml version="1.0"?><w:document xmlns:w="x">'
        "<w:p><w:r><w:t>第一段</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>第二段</w:t></w:r></w:p></w:document>"
    )
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr("word/document.xml", xml)
    text = loaders.load_text(docx)
    assert "第一段" in text and "第二段" in text


def test_load_text_errors(tmp_path):
    with pytest.raises(NotFoundError):
        loaders.load_text(tmp_path / "missing.txt")

    bad = tmp_path / "x.bin"
    bad.write_bytes(b"\x00\x01")
    with pytest.raises(BadRequestError):
        loaders.load_text(bad)
