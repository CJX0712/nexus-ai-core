/** 对话面板：调用 /v1/chat，可切换是否启用知识库增强。
 *  作者: 晨星 */
import { useState } from "react";
import { Bot, Send, User } from "lucide-react";
import { api } from "../lib/api";
import type { ChatResponse } from "../lib/types";

interface Turn {
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
}

export default function ChatPanel() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [session, setSession] = useState("console");
  const [useRag, setUseRag] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    setInput("");
    setTurns((t) => [...t, { role: "user", content: text }]);
    try {
      const res = await api.chat(text, session, useRag, 4);
      setTurns((t) => [...t, { role: "assistant", content: res.answer, meta: res }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="card">
        <div className="row">
          <input
            className="grow"
            type="text"
            value={session}
            onChange={(e) => setSession(e.target.value)}
            aria-label="会话 ID"
          />
          <label className="row" style={{ gap: 6 }}>
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
            />
            <span className="muted">启用知识库</span>
          </label>
        </div>
      </div>

      <div className="card">
        {turns.length === 0 ? (
          <div className="empty">
            还没有对话。先到「知识库」入库资料，再回来开启知识库提问，可得到带溯源来源的答案。
          </div>
        ) : (
          <div className="messages">
            {turns.map((t, i) => (
              <div key={i} className={`msg msg-${t.role}`}>
                <span className="msg-avatar">
                  {t.role === "user" ? <User size={14} /> : <Bot size={14} />}
                </span>
                <div>
                  <div className="msg-body">{t.content}</div>
                  {t.meta && (
                    <div className="row" style={{ marginTop: 6, gap: 6, flexWrap: "wrap" }}>
                      <span className="pill pill-accent">{t.meta.provider}</span>
                      <span className="pill">{t.meta.latency_ms} ms</span>
                      {t.meta.sources.length > 0 && (
                        <span className="pill">来源 {t.meta.sources.length}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <div className="card" style={{ borderColor: "var(--c-danger)" }}>{error}</div>}

      <div className="card">
        <textarea
          value={input}
          placeholder="输入问题，Ctrl+Enter 发送"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              void send();
            }
          }}
        />
        <div className="row row-end" style={{ marginTop: "var(--s-3)" }}>
          <button className="btn btn-primary" type="button" onClick={() => void send()} disabled={busy || !input.trim()}>
            <Send size={15} />
            {busy ? "生成中" : "发送"}
          </button>
        </div>
      </div>
    </div>
  );
}
