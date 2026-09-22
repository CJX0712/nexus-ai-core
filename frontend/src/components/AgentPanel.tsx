/** 智能体面板：运行 ReAct 智能体并可视化每一步的思考/行动/观察。
 *  作者: 晨星 */
import { useState } from "react";
import { Bot, Play } from "lucide-react";
import { api } from "../lib/api";
import type { AgentResponse } from "../lib/types";

export default function AgentPanel() {
  const [task, setTask] = useState("");
  const [steps, setSteps] = useState(4);
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!task.trim() || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.agentRun(task.trim(), "agent-console", steps));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="card">
        <h2 className="card-title">任务</h2>
        <p className="card-hint">
          智能体会自行决定调用哪个工具（知识检索 / 计算器 / 记忆 / 时间），最多执行指定步数后给出结论。
        </p>
        <textarea
          value={task}
          placeholder="例如：先检索知识库里关于模块划分的内容，再总结成三点"
          onChange={(e) => setTask(e.target.value)}
        />
        <div className="row" style={{ marginTop: "var(--s-2)" }}>
          <label className="row" style={{ gap: 6 }}>
            <span className="muted">最大步数</span>
            <input
              type="number"
              min={1}
              max={12}
              value={steps}
              onChange={(e) => setSteps(Number(e.target.value))}
              style={{ width: 84 }}
            />
          </label>
          <button className="btn btn-primary" type="button" onClick={() => void run()} disabled={busy || !task.trim()}>
            <Play size={15} /> {busy ? "执行中" : "运行"}
          </button>
        </div>
      </div>

      {error && <div className="card" style={{ borderColor: "var(--c-danger)" }}>{error}</div>}

      {result && (
        <>
          <div className="card">
            <h2 className="card-title">结论</h2>
            <div className="row" style={{ marginBottom: "var(--s-2)", gap: 6, flexWrap: "wrap" }}>
              <span className="pill pill-accent">{result.provider}</span>
              <span className="pill">工具调用 {result.tool_calls}</span>
              <span className={`pill ${result.finished ? "pill-ok" : "pill-warn"}`}>
                {result.finished ? "已完成" : "达到步数上限"}
              </span>
            </div>
            <div className="msg-body">{result.answer}</div>
          </div>

          <div className="card">
            <h2 className="card-title">执行轨迹</h2>
            {result.steps.length === 0 ? (
              <div className="empty">无中间步骤</div>
            ) : (
              <div className="list">
                {result.steps.map((s, i) => (
                  <div key={i} className="list-item">
                    <div className="row" style={{ gap: 6 }}>
                      <Bot size={14} />
                      <strong>步骤 {i + 1}</strong>
                      {s.action && <span className="pill pill-accent">{s.action}</span>}
                    </div>
                    {s.thought && <p className="muted" style={{ margin: "6px 0 0" }}>思考：{s.thought}</p>}
                    {s.action_input && (
                      <div className="code-block" style={{ marginTop: 6 }}>{s.action_input}</div>
                    )}
                    {s.observation && (
                      <p style={{ margin: "6px 0 0" }}>观察：{s.observation}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
