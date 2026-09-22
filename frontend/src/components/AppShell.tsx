/** 应用外壳：左侧导航 + 顶部状态栏。图标统一使用 lucide 描边 SVG。
 *  作者: 晨星 */
import type { ReactNode } from "react";
import {
  Activity, Bot, Database, MessageSquare, Sparkles, Workflow,
} from "lucide-react";
import type { HealthResponse } from "../lib/types";

export type ViewKey = "chat" | "knowledge" | "agent" | "workflow" | "system";

export interface ViewDef {
  key: ViewKey;
  label: string;
  hint: string;
  icon: ReactNode;
}

export const VIEWS: ViewDef[] = [
  { key: "chat", label: "对话", hint: "网关 + 可选知识库问答", icon: <MessageSquare size={16} /> },
  { key: "knowledge", label: "知识库", hint: "入库、检索与溯源问答", icon: <Database size={16} /> },
  { key: "agent", label: "智能体", hint: "ReAct 推理与工具调用", icon: <Bot size={16} /> },
  { key: "workflow", label: "工作流", hint: "DAG 编排与执行", icon: <Workflow size={16} /> },
  { key: "system", label: "系统状态", hint: "模块健康与自描述", icon: <Activity size={16} /> },
];

interface Props {
  active: ViewKey;
  onSelect: (key: ViewKey) => void;
  health: HealthResponse | null;
  title: string;
  children: ReactNode;
}

export default function AppShell({ active, onSelect, health, title, children }: Props) {
  const current = VIEWS.find((v) => v.key === active);
  const online = health?.status === "ok";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><Sparkles size={16} /></span>
          <span>
            <div className="brand-name">NexusAI</div>
            <div className="brand-sub">AI 能力中台</div>
          </span>
        </div>

        <nav className="nav">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              type="button"
              className={`nav-item${v.key === active ? " is-active" : ""}`}
              onClick={() => onSelect(v.key)}
            >
              {v.icon}
              <span>{v.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="mono">v{health?.version ?? "-"}</div>
          <div>作者 晨星</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <h1>{title}</h1>
          <div className="topbar-meta">
            {current && <span className="faint">{current.hint}</span>}
            <span className={`pill ${online ? "pill-ok" : "pill-danger"}`}>
              {online ? "服务在线" : "未连接"}
            </span>
          </div>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
