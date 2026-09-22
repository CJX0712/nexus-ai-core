/** 工作流面板：以 JSON 定义 DAG 节点并执行，展示拓扑顺序与输出。
 *  作者: 晨星 */
import { useState } from "react";
import { Play, Workflow } from "lucide-react";
import { api } from "../lib/api";
import type { WorkflowNode, WorkflowResponse } from "../lib/types";

const PRESET: WorkflowNode[] = [
  { id: "topic", kind: "transform", params: { template: "主题:{input}" }, depends_on: [] },
  { id: "recall", kind: "rag", params: { query: "{input}", top_k: 3 }, depends_on: [] },
  { id: "calc", kind: "tool", params: { name: "calculator", args: { expression: "6*7" } }, depends_on: ["topic"] },
];

const PRESET_TEXT = JSON.stringify(PRESET, null, 2);

export default function WorkflowPanel() {
  const [nodesText, setNodesText] = useState(PRESET_TEXT);
  const [input, setInput] = useState("模块化");
  const [result, setResult] = useState<WorkflowResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const nodes = JSON.parse(nodesText) as WorkflowNode[];
      setResult(await api.workflowRun(nodes, input));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="card">
        <h2 className="card-title">节点定义</h2>
        <p className="card-hint">
          节点类型：transform（模板渲染）、rag（知识检索）、tool（工具调用）、llm（模型生成）。
          depends_on 声明依赖，引擎自动拓扑排序，存在环会报错。
        </p>
        <textarea
          className="mono"
          value={nodesText}
          onChange={(e) => setNodesText(e.target.value)}
          style={{ minHeight: 200 }}
        />
        <div className="row" style={{ marginTop: "var(--s-2)" }}>
          <input
            className="grow"
            type="text"
            value={input}
            placeholder="工作流输入"
            onChange={(e) => setInput(e.target.value)}
          />
          <button className="btn btn-primary" type="button" onClick={() => void run()} disabled={busy}>
            <Play size={15} /> {busy ? "执行中" : "运行工作流"}
          </button>
        </div>
      </div>

      {error && <div className="card" style={{ borderColor: "var(--c-danger)" }}>{error}</div>}

      {result && (
        <div className="card">
          <h2 className="card-title">执行结果</h2>
          <div className="row" style={{ marginBottom: "var(--s-3)", gap: 6, flexWrap: "wrap" }}>
            <Workflow size={14} />
            <span className="muted">拓扑顺序：</span>
            {result.order.map((id) => (
              <span key={id} className="pill pill-accent">{id}</span>
            ))}
          </div>
          <div className="list">
            {Object.entries(result.outputs).map(([id, out]) => (
              <div key={id} className="list-item">
                <strong className="mono">{id}</strong>
                <div className="code-block" style={{ marginTop: 6 }}>
                  {typeof out === "string" ? out : JSON.stringify(out, null, 2)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
