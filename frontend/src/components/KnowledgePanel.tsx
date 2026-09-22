/** 知识库面板：入库（文本/文件）、检索、溯源问答。
 *  作者: 晨星 */
import { useRef, useState } from "react";
import { FileUp, Plus, Search, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import type { AskResponse, IngestResponse, SearchHit } from "../lib/types";

export default function KnowledgePanel() {
  const [text, setText] = useState("");
  const [source, setSource] = useState("manual.md");
  const [ingestMsg, setIngestMsg] = useState<string | null>(null);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [query, setQuery] = useState("");
  const [ask, setAsk] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function ingestText() {
    return run(async () => {
      const res: IngestResponse = await api.ingest(text, source || "manual.md");
      setIngestMsg(`已入库 ${res.source}，切分为 ${res.n_chunks} 个片段，doc_id=${res.doc_id}`);
      setText("");
    });
  }

  async function upload(file: File) {
    await run(async () => {
      const res = await api.ingestFile(file);
      setIngestMsg(`已入库 ${res.source}，切分为 ${res.n_chunks} 个片段，doc_id=${res.doc_id}`);
    });
  }

  return (
    <div className="panel">
      <div className="card">
        <h2 className="card-title">入库</h2>
        <p className="card-hint">支持 .txt / .md / .pdf / .docx / .html，自动分块、嵌入并写入 FAISS。</p>
        <textarea
          value={text}
          placeholder="粘贴要入库的文本"
          onChange={(e) => setText(e.target.value)}
        />
        <div className="row" style={{ marginTop: "var(--s-2)" }}>
          <input
            type="text"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            aria-label="来源名称"
            style={{ maxWidth: 220 }}
          />
          <button className="btn btn-primary" type="button" disabled={busy || !text.trim()} onClick={() => void ingestText()}>
            <Plus size={15} /> 文本入库
          </button>
          <button className="btn" type="button" disabled={busy} onClick={() => fileRef.current?.click()}>
            <FileUp size={15} /> 上传文件
          </button>
          <input
            ref={fileRef}
            type="file"
            hidden
            accept=".txt,.md,.markdown,.pdf,.docx,.html,.htm"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void upload(f);
              e.target.value = "";
            }}
          />
        </div>
        {ingestMsg && <p className="mono muted" style={{ marginTop: "var(--s-2)" }}>{ingestMsg}</p>}
      </div>

      <div className="card">
        <h2 className="card-title">检索</h2>
        <div className="row">
          <input
            className="grow"
            type="text"
            value={query}
            placeholder="输入检索关键词"
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            className="btn"
            type="button"
            disabled={busy || !query.trim()}
            onClick={() => run(async () => setHits(await api.search(query, 4)))}
          >
            <Search size={15} /> 检索
          </button>
          <button
            className="btn btn-primary"
            type="button"
            disabled={busy || !query.trim()}
            onClick={() => run(async () => setAsk(await api.ask(query, 4)))}
          >
            <Sparkles size={15} /> 溯源问答
          </button>
        </div>
      </div>

      {error && <div className="card" style={{ borderColor: "var(--c-danger)" }}>{error}</div>}

      {ask && (
        <div className="card">
          <h2 className="card-title">答案</h2>
          <div className="row" style={{ marginBottom: "var(--s-2)", gap: 6, flexWrap: "wrap" }}>
            <span className="pill pill-accent">{ask.provider}</span>
            <span className="pill">{ask.latency_ms} ms</span>
          </div>
          <div className="msg-body">{ask.answer}</div>
        </div>
      )}

      {(hits.length > 0 || ask) && (
        <div className="card">
          <h2 className="card-title">{hits.length > 0 ? "检索命中" : "引用来源"}</h2>
          <div className="list">
            {(hits.length > 0 ? hits.map((h) => ({
              score: h.score,
              label: String(h.metadata.source ?? h.doc_id),
              text: h.text,
            })) : (ask?.sources ?? []).map((s) => ({
              score: s.score,
              label: s.source || s.doc_id,
              text: s.snippet,
            }))).map((item, i) => (
              <div key={i} className="list-item">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <strong className="mono">{item.label}</strong>
                  <span className="pill">{item.score.toFixed(4)}</span>
                </div>
                <p className="muted" style={{ margin: "6px 0 0" }}>{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
