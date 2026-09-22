"""记忆模块（单一职责：只负责会话记忆的写入、读取与检索）。

短期记忆：进程内环形缓冲（最近 N 轮）
长期记忆：SQLite 落盘，支持关键词召回

作者: 晨星
"""
from __future__ import annotations

import sqlite3
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

log = get_logger("memory.store")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'chat',
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


class MemoryStore:
    """会话记忆存储。"""

    def __init__(self, db_path: str | Path, max_turns: int = 20) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_turns = max_turns
        self._buffer: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_turns * 2))
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---------- 写 ----------
    def add(self, session_id: str, role: str, content: str,
            kind: str = "chat") -> int:
        ts = time.time()
        cur = self._conn.execute(
            "INSERT INTO messages(session_id, role, content, kind, ts) VALUES(?,?,?,?,?)",
            (session_id, role, content, kind, ts),
        )
        self._conn.commit()
        self._buffer[session_id].append({"role": role, "content": content,
                                         "kind": kind, "ts": ts})
        return int(cur.lastrowid or 0)

    def remember(self, session_id: str, content: str) -> int:
        """写入一条长期记忆（kind=note，不占用短期窗口）。"""
        return self.add(session_id, "note", content, kind="note")

    # ---------- 读 ----------
    def recent(self, session_id: str, n: int | None = None) -> list[dict]:
        """最近 N 条（短期记忆）。"""
        limit = n or self.max_turns * 2
        rows = self._conn.execute(
            "SELECT role, content, kind, ts FROM messages "
            "WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, int(limit)),
        ).fetchall()
        return [{"role": r[0], "content": r[1], "kind": r[2], "ts": r[3]}
                for r in reversed(rows)]

    def recall(self, session_id: str, query: str, limit: int = 5) -> list[dict]:
        """关键词召回历史内容（跨短期窗口）。"""
        terms = [t for t in query.split() if len(t) >= 2]
        if not terms:
            return self.recent(session_id, limit)
        where = " AND ".join(["content LIKE ?"] * len(terms))
        params: list[Any] = [session_id]
        params.extend(f"%{t}%" for t in terms)
        rows = self._conn.execute(
            f"SELECT role, content, kind, ts FROM messages "  # noqa: S608 - 条件由占位符拼装
            f"WHERE session_id=? AND ({where}) ORDER BY id DESC LIMIT ?",
            (*params, int(limit)),
        ).fetchall()
        return [{"role": r[0], "content": r[1], "kind": r[2], "ts": r[3]}
                for r in rows]

    def stats(self, session_id: str | None = None) -> dict:
        if session_id:
            n = self._conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id=?", (session_id,)
            ).fetchone()[0]
            return {"session": session_id, "messages": int(n)}
        total = self._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        sessions = self._conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM messages"
        ).fetchone()[0]
        return {"total_messages": int(total), "sessions": int(sessions)}

    def clear(self, session_id: str) -> int:
        cur = self._conn.execute(
            "DELETE FROM messages WHERE session_id=?", (session_id,)
        )
        self._conn.commit()
        self._buffer.pop(session_id, None)
        return int(cur.rowcount or 0)

    def close(self) -> None:
        self._conn.close()
