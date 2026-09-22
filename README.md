# NexusAI · 模块化 AI 能力中台

> 一套端到端可运行的 AI 系统开发环境：优先整合复用业界领先开源成果，
> 按单一职责划分模块，每个模块可独立验证，又能协同组成完整链路。
>
> 作者：晨星

---

## 一、它是什么

NexusAI 是一个**AI 能力中台**（AI Capability Platform）。它不重复造轮子，而是把业界成熟的开源 AI 组件整合为统一契约下的五个核心模块，并通过 REST API 与 Web 控制台对外提供能力：

| 能力 | 说明 |
|------|------|
| 统一模型网关 | 一套接口对接任意 OpenAI 兼容服务 + 本地 GGUF，自动降级 |
| 检索增强生成 | 文档入库 → 分块 → 向量化 → 稠密+稀疏混合检索 → 带溯源应答 |
| 智能体编排 | ReAct 推理循环 + 工具注册表（知识检索/计算/记忆/时间） |
| 工作流引擎 | DAG 拓扑调度，把各模块编排成可复用管线 |
| 记忆 | 短期会话窗口 + SQLite 长期落盘，支持关键词召回 |

**关键特性**：没有任何 API Key、没有网络、没有 GPU 时，系统依然能完整跑通链路（自动降级到离线抽取式应答 + 本地哈希嵌入），保证"构建即可运行、运行即可验证"。

---

## 二、模块划分（单一职责）

| 编号 | 模块 | 路径 | 单一职责 | 核心接口 |
|------|------|------|----------|----------|
| M1 | 模型网关 | `backend/app/gateway/` | 屏蔽 provider 差异，统一对话与嵌入 | `complete(messages)` / `embed(texts)` |
| M2 | 知识检索 | `backend/app/rag/` | 加载→分块→嵌入→入库→混合检索 | `ingest_text()` / `search()` / `answer()` |
| M3 | 智能体 | `backend/app/agent/` | 推理-行动-观察循环与工具调度 | `run(task)` / `registry.call(name)` |
| M4 | 工作流 | `backend/app/workflow/` | DAG 拓扑排序与节点执行 | `run(nodes, input)` |
| M5 | 记忆 | `backend/app/memory/` | 会话记忆写入、读取、召回 | `add()` / `recent()` / `recall()` |
| M6 | API 服务 | `backend/app/api/` | 暴露 REST 契约（OpenAPI 3.0） | `/v1/*` |
| M7 | 控制台 | `frontend/` | 对话/知识库/智能体/工作流可视化 | REST 客户端 |
| M8 | 可观测 | `backend/app/core/` | 配置、日志、结构化错误、健康检查 | `/health` |

**调用关系**：

```
控制台(M7) → API(M6)
               └→ 智能体(M3) ──→ 模型网关(M1)（云端 API / 本地 GGUF / 离线 三级降级）
                    ├→ 知识检索(M2) ← M1(嵌入)
                    ├→ 记忆(M5)
                    └→ 工作流(M4)（可选编排 M1/M2/M5）
```

各模块通过构造函数注入依赖，**互不 new**，因此每个模块都能脱离其他模块单独实例化与测试。装配集中在唯一的组合根 `backend/app/container.py`。

---

## 三、整合的开源成果

| 组件 | 用途 | 选型理由 |
|------|------|----------|
| [FastAPI](https://github.com/fastapi/fastapi) | REST 服务层 | 自动生成 OpenAPI、异步、类型安全 |
| [FAISS](https://github.com/facebookresearch/faiss)（Meta） | 稠密向量检索 | 业界标准向量检索引擎，CPU 即可跑 |
| [fastembed](https://github.com/qdrant/fastembed)（Qdrant） | 文本嵌入 | ONNX 本地推理，**无需 torch**，CPU 友好 |
| [rank_bm25](https://github.com/dorianbrown/rank_bm25) | 稀疏检索 | 与稠密检索 RRF 融合，兼顾语义与关键词 |
| [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) | 本地 GGUF 推理 | llama.cpp 官方绑定，无 GPU 也能跑量化模型 |
| [pypdf](https://github.com/py-pdf/pypdf) | PDF 解析 | 纯 Python，零系统依赖 |
| [loguru](https://github.com/Delgan/loguru) | 结构化日志 | 开箱即用，配置极简 |
| React + Vite + lucide-react | 控制台 | 描边 SVG 图标，无 emoji，轻量可维护 |

---

## 四、快速开始

### 方式一：Docker 一键起（推荐）

```bash
cp .env.example .env      # 可选：填入你的 LLM API Key
docker compose up --build
```

- 控制台：http://localhost:8080
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 方式二：本地直跑（免 Docker）

```bash
# 后端
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r backend/requirements.lock.txt
cd backend && python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# 前端（另开终端）
cd frontend && npm install && npm run dev              # http://localhost:5173
```

### 30 秒验证链路

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"text":"NexusAI 由模型网关、知识检索、智能体编排、工作流引擎、记忆五个模块组成。","source":"arch.md"}'

curl -X POST http://localhost:8000/v1/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"NexusAI 由哪些模块组成？","top_k":3}'
```

---

## 五、接入真实大模型

默认 `NEXUS_LLM_PROVIDER=auto`，降级顺序为：**云端 OpenAI 兼容 API → 本地 GGUF → 离线抽取式**。

```bash
# 例：接入 DeepSeek
NEXUS_LLM_BASE_URL=https://api.deepseek.com/v1
NEXUS_LLM_API_KEY=sk-xxxx
NEXUS_LLM_MODEL=deepseek-chat
```

凡是兼容 OpenAI `/v1/chat/completions` 协议的服务均可直接接入（OpenAI、DeepSeek、通义千问、Moonshot、Groq、Ollama、vLLM 等），**无需改动任何代码**。

---

## 六、目录结构

```
nexus-ai-core/
├── backend/
│   ├── app/
│   │   ├── core/        配置 / 日志 / 错误模型
│   │   ├── gateway/     M1 模型网关（嵌入 + 对话）
│   │   ├── rag/         M2 加载器 / 分块 / 向量库 / 混合检索 / 服务
│   │   ├── agent/       M3 工具注册表 + ReAct 循环
│   │   ├── workflow/    M4 DAG 引擎
│   │   ├── memory/      M5 记忆存储
│   │   ├── api/         M6 路由 / 契约模型 / 应用工厂
│   │   └── container.py 组合根（唯一依赖装配点）
│   ├── tests/           8 个测试文件，67 条用例
│   ├── requirements.in / requirements.lock.txt
│   └── Dockerfile
├── frontend/            M7 React + TS 控制台
├── docs/                架构 / 部署 / 使用 / SPEC
├── docker-compose.yml   一键编排
└── Makefile             常用命令入口
```

---

## 七、API 一览

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 健康检查与各模块装配状态 |
| GET | `/v1/stats` | 系统自描述（嵌入/模型链/工具/知识库） |
| GET | `/v1/models` | 当前可用模型提供方 |
| POST | `/v1/chat` | 对话（可开关知识库增强） |
| POST | `/v1/rag/ingest` | 文本入库 |
| POST | `/v1/rag/ingest-file` | 文件上传入库（txt/md/pdf/docx/html） |
| POST | `/v1/rag/search` | 混合检索 |
| POST | `/v1/rag/ask` | 带溯源的检索增强问答 |
| POST | `/v1/agent/run` | 运行 ReAct 智能体 |
| POST | `/v1/workflow/run` | 执行 DAG 工作流 |
| GET/POST/DELETE | `/v1/memory/{session}` | 记忆读写、召回、清空 |

完整契约见运行时的 `/docs`（Swagger UI）与 `/openapi.json`。

---

## 八、验证状态

| 项 | 结果 |
|----|------|
| 后端单元测试 | 67 条用例全部通过 |
| 静态检查 | `ruff check` 零告警 |
| 真实服务启动 | uvicorn 启动成功，全链路请求验证通过 |
| 前端类型检查 | `tsc --noEmit` 零错误 |
| 前端生产构建 | Vite 构建成功（167 KB JS / 5.9 KB CSS） |
| 离线可运行 | 无 Key、无网络、无 GPU 仍可跑通入库→检索→应答 |

---

## 九、文档

- [系统架构](docs/架构.md) —— 模块划分、接口契约、调用关系、设计决策
- [部署指南](docs/部署指南.md) —— 本地 / Docker / 云端部署与回滚
- [使用指南](docs/使用指南.md) —— API 调用示例、控制台用法、扩展新模块
- [规格契约 SPEC](docs/SPEC.md) —— 范围锁定、验收标准、端到端验证步骤

---

## 十、许可与署名

MIT License · 作者：晨星
