"""记忆模块测试：短期窗口 / 长期落盘 / 关键词召回。

作者: 晨星
"""
from __future__ import annotations

from pathlib import Path

from app.memory.store import MemoryStore


def test_memory_add_and_recent(tmp_path):
    m = MemoryStore(tmp_path / "m.db", max_turns=10)
    m.add("s1", "user", "第一条消息")
    m.add("s1", "assistant", "第二条回复")
    recent = m.recent("s1")
    assert [r["content"] for r in recent] == ["第一条消息", "第二条回复"]


def test_memory_isolated_by_session(tmp_path):
    m = MemoryStore(tmp_path / "m.db")
    m.add("s1", "user", "会话一内容")
    m.add("s2", "user", "会话二内容")
    assert len(m.recent("s1")) == 1
    assert m.recent("s1")[0]["content"] == "会话一内容"


def test_memory_recall_by_keyword(tmp_path):
    m = MemoryStore(tmp_path / "m.db")
    m.add("s1", "user", "今天讨论了向量数据库的选型")
    m.add("s1", "user", "明天要去深圳出差")
    hits = m.recall("s1", "向量数据库")
    assert len(hits) == 1 and "向量数据库" in hits[0]["content"]


def test_memory_recall_falls_back_to_recent_when_no_term(tmp_path):
    m = MemoryStore(tmp_path / "m.db")
    m.add("s1", "user", "内容A")
    assert len(m.recall("s1", "的")) == 1


def test_memory_remember_note(tmp_path):
    m = MemoryStore(tmp_path / "m.db")
    m.remember("s1", "用户偏好中文回答")
    items = m.recent("s1")
    assert items[0]["kind"] == "note"
    assert "中文回答" in m.recall("s1", "偏好")[0]["content"]


def test_memory_clear_and_stats(tmp_path):
    m = MemoryStore(tmp_path / "m.db")
    m.add("s1", "user", "x")
    m.add("s2", "user", "y")
    assert m.stats()["sessions"] == 2
    assert m.clear("s1") == 1
    assert m.stats("s1")["messages"] == 0
    assert m.stats()["total_messages"] == 1


def test_memory_persists_to_sqlite(tmp_path):
    path = tmp_path / "m.db"
    m1 = MemoryStore(path)
    m1.add("s1", "user", "持久化验证")
    m1.close()

    assert Path(path).exists()
    m2 = MemoryStore(path)
    assert m2.recent("s1")[0]["content"] == "持久化验证"
