"""文本分块器（单一职责：只负责把长文本切成可检索片段）。

递归分隔符切分，中文优先按句读切，保证 chunk_size 内语义完整。

作者: 晨星
"""
from __future__ import annotations

import re

SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", ". ", "! ", "? ", "；", " ", ""]


def _split_by(text: str, sep: str) -> list[str]:
    if sep == "":
        return list(text)
    parts = text.split(sep)
    return [p + sep if sep in ("。", "！", "？", "；") else p for p in parts]


def _recursive_split(text: str, chunk_size: int, seps: list[str]) -> list[str]:
    if len(text) <= chunk_size or not seps:
        return [text] if text.strip() else []
    sep, rest = seps[0], seps[1:]
    chunks: list[str] = []
    buf = ""
    for piece in _split_by(text, sep):
        if len(buf) + len(piece) <= chunk_size:
            buf += piece
            continue
        if buf:
            chunks.append(buf)
        if len(piece) > chunk_size:
            chunks.extend(_recursive_split(piece, chunk_size, rest))
            buf = ""
        else:
            buf = piece
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c.strip()]


def _merge_small(chunks: list[str], chunk_size: int) -> list[str]:
    """把过短片段并入相邻块，减少碎片。"""
    merged: list[str] = []
    for c in chunks:
        if merged and len(merged[-1]) + len(c) <= chunk_size:
            merged[-1] += c
        else:
            merged.append(c)
    return merged


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """切分并施加重叠，返回 chunk 列表。"""
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    raw = _recursive_split(text, chunk_size, SEPARATORS)
    raw = _merge_small(raw, chunk_size)
    if overlap <= 0 or len(raw) <= 1:
        return raw

    out: list[str] = []
    for i, c in enumerate(raw):
        if i == 0:
            out.append(c)
            continue
        tail = raw[i - 1][-overlap:]
        out.append(tail + c)
    return out
