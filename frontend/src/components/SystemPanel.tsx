/** 系统状态面板：展示各模块装配结果与可观测指标。
 *  作者: 晨星 */
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import type { ModelInfo, StatsResponse } from "../lib/types";

export default function SystemPanel() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [s, m] = await Promise.all([api.stats(), api.models()]);
      setStats(s);
      setModels(m);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

  return (
    <div className="panel">
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 className="card-title">模块装配</h2>
          <button className="btn" type="button" onClick={() => void load()} disabled={busy}>
            <RefreshCw size={15} /> 刷新
          </button>
        </div>
        {error && <p style={{ color: "var(--c-danger)" }}>{error}</p>}
        {stats && (
          <dl className="kv">
            <dt>应用</dt><dd>{stats.app} <span className="faint">v{stats.version}</span></dd>
            <dt>嵌入提供方</dt><dd className="mono">{stats.embedding.provider}（dim={stats.embedding.dim}）</dd>
            <dt>模型降级链</dt><dd>{stats.llm_chain.join(" → ")}</dd>
            <dt>已注册工具</dt><dd>{stats.tools.join("、") || "无"}</dd>
            <dt>知识库</dt><dd>{stats.rag.documents} 篇文档 / {stats.rag.chunks} 个片段</dd>
          </dl>
        )}
      </div>

      <div className="card">
        <h2 className="card-title">可用模型</h2>
        {models.length === 0 ? (
          <div className="empty">未探测到模型</div>
        ) : (
          <div className="list">
            {models.map((m, i) => (
              <div key={i} className="list-item row" style={{ justifyContent: "space-between" }}>
                <strong>{m.provider}</strong>
                <span className="pill">{m.model}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h2 className="card-title">接口自描述</h2>
        <p className="card-hint">
          后端自动生成 OpenAPI 3.0 契约，可直接查看或用于生成客户端代码。
        </p>
        <div className="row">
          <a className="btn" href="/docs" target="_blank" rel="noreferrer">Swagger UI</a>
          <a className="btn" href="/openapi.json" target="_blank" rel="noreferrer">openapi.json</a>
        </div>
      </div>
    </div>
  );
}
