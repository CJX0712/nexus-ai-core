/** NexusAI 控制台根组件：视图切换 + 健康检查轮询。
 *  作者: 晨星 */
import { useEffect, useState } from "react";
import AppShell, { VIEWS, type ViewKey } from "./components/AppShell";
import ChatPanel from "./components/ChatPanel";
import KnowledgePanel from "./components/KnowledgePanel";
import AgentPanel from "./components/AgentPanel";
import WorkflowPanel from "./components/WorkflowPanel";
import SystemPanel from "./components/SystemPanel";
import { api } from "./lib/api";
import type { HealthResponse } from "./lib/types";

export default function App() {
  const [view, setView] = useState<ViewKey>("chat");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let alive = true;
    const probe = async () => {
      try {
        const h = await api.health();
        if (alive) setHealth(h);
      } catch {
        if (alive) setHealth(null);
      }
    };
    void probe();
    const timer = window.setInterval(() => void probe(), 15000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, []);

  const title = VIEWS.find((v) => v.key === view)?.label ?? "NexusAI";

  return (
    <AppShell active={view} onSelect={setView} health={health} title={title}>
      {view === "chat" && <ChatPanel />}
      {view === "knowledge" && <KnowledgePanel />}
      {view === "agent" && <AgentPanel />}
      {view === "workflow" && <WorkflowPanel />}
      {view === "system" && <SystemPanel />}
    </AppShell>
  );
}
