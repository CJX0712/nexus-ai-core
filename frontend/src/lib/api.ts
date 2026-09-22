/** 后端 REST 客户端：所有请求走同源 /v1，由 Vite 或 Nginx 代理到 FastAPI。
 *  作者: 晨星 */
import type {
  AgentResponse, AskResponse, ChatResponse, HealthResponse, IngestResponse,
  MemoryItem, ModelInfo, SearchHit, StatsResponse, WorkflowNode, WorkflowResponse,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, init);
  } catch (err) {
    throw new ApiError("network_error",
      `无法连接后端服务（${String(err)}）。请确认 API 已启动，或设置 VITE_API_BASE。`);
  }
  const text = await resp.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!resp.ok) {
    const err = (body as { error?: { code?: string; message?: string } } | null)
      ?.error;
    throw new ApiError(err?.code ?? "http_error",
      err?.message ?? `请求失败 (HTTP ${resp.status})`);
  }
  return body as T;
}

const json = (method: string, payload: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

export const api = {
  health: () => request<HealthResponse>("/health"),
  stats: () => request<StatsResponse>("/v1/stats"),
  models: () => request<ModelInfo[]>("/v1/models"),

  chat: (message: string, sessionId: string, useRag: boolean, topK: number) =>
    request<ChatResponse>("/v1/chat", json("POST", {
      message, session_id: sessionId, use_rag: useRag, top_k: topK,
    })),

  ingest: (text: string, source: string) =>
    request<IngestResponse>("/v1/rag/ingest", json("POST", { text, source })),

  ingestFile: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`${BASE}/v1/rag/ingest-file`, {
      method: "POST", body: form,
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => null);
      const err = (body as { error?: { code?: string; message?: string } } | null)
        ?.error;
      throw new ApiError(err?.code ?? "http_error",
        err?.message ?? `上传失败 (HTTP ${resp.status})`);
    }
    return (await resp.json()) as IngestResponse;
  },

  search: (query: string, topK: number) =>
    request<SearchHit[]>("/v1/rag/search", json("POST", { query, top_k: topK })),

  ask: (question: string, topK: number) =>
    request<AskResponse>("/v1/rag/ask", json("POST", { question, top_k: topK })),

  agentRun: (task: string, sessionId: string, maxSteps: number) =>
    request<AgentResponse>("/v1/agent/run", json("POST", {
      task, session_id: sessionId, max_steps: maxSteps,
    })),

  workflowRun: (nodes: WorkflowNode[], input: string) =>
    request<WorkflowResponse>("/v1/workflow/run", json("POST", { nodes, input })),

  memoryList: (session: string, n = 20) =>
    request<MemoryItem[]>(`/v1/memory/${encodeURIComponent(session)}?n=${n}`),

  memoryAdd: (session: string, role: string, content: string) =>
    request<{ id: number; session_id: string }>(
      `/v1/memory/${encodeURIComponent(session)}`,
      json("POST", { role, content })),

  memoryClear: (session: string) =>
    request<{ deleted: number }>(`/v1/memory/${encodeURIComponent(session)}`,
      { method: "DELETE" }),
};
