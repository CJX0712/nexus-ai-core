/** 与后端 app/api/schemas.py 一一对应的契约类型。
 *  作者: 晨星 */

export interface HealthResponse {
  status: string;
  version: string;
  embedding_provider: string;
  llm_chain: string[];
  rag_chunks: number;
  documents: number;
}

export interface StatsResponse {
  app: string;
  version: string;
  embedding: { provider: string; dim: number | null };
  llm_chain: string[];
  tools: string[];
  rag: {
    documents: number;
    chunks: number;
    embedding_dim: number | null;
    embedding_provider: string;
  };
}

export interface ModelInfo {
  provider: string;
  model: string;
}

export interface Source {
  doc_id: string;
  score: number;
  source: string;
  snippet: string;
}

export interface ChatResponse {
  answer: string;
  provider: string;
  model: string;
  session_id: string;
  sources: Source[];
  latency_ms: number;
}

export interface SearchHit {
  score: number;
  text: string;
  doc_id: string;
  chunk_id: number;
  metadata: Record<string, unknown>;
}

export interface AskResponse {
  answer: string;
  provider: string;
  model: string;
  sources: Source[];
  latency_ms: number;
}

export interface IngestResponse {
  doc_id: string;
  n_chunks: number;
  source: string;
}

export interface AgentStep {
  thought: string;
  action: string;
  action_input: string;
  observation: string;
  final: string;
}

export interface AgentResponse {
  answer: string;
  finished: boolean;
  tool_calls: number;
  provider: string;
  model: string;
  steps: AgentStep[];
}

export interface WorkflowNode {
  id: string;
  kind: "llm" | "rag" | "tool" | "transform";
  params: Record<string, unknown>;
  depends_on: string[];
}

export interface WorkflowResponse {
  order: string[];
  outputs: Record<string, unknown>;
}

export interface MemoryItem {
  role: string;
  content: string;
  kind: string;
  ts: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; detail?: unknown };
}
