# Spec · NexusAI 模块化 AI 能力中台 v1.0.0

> 生成日期：2026-09-23
> 状态：已确认
> 作者：晨星

---

## 1. 产品定义

- **一句话描述**：整合业界领先开源 AI 组件的模块化能力中台，各模块单一职责、可独立验证、可协同成链。
- **目标用户**：需要快速搭建可运行 AI 系统的研发团队与独立开发者。
- **核心问题**：AI 系统各能力耦合严重、环境依赖脆弱、缺少 Key 或 GPU 就无法验证。

## 2. MVP 范围（锁定）

| 优先级 | 功能 | 验收标准摘要 |
|--------|------|--------------|
| P0 | 统一模型网关 | 一套接口对接 OpenAI 兼容服务与本地 GGUF；失败自动降级 |
| P0 | 知识库入库 | 支持 txt/md/pdf/docx/html；分块后写入向量库并落盘 |
| P0 | 混合检索 | 稠密+稀疏 RRF 融合，结果按分数降序 |
| P0 | 溯源问答 | 回答必须携带 sources（doc_id/score/snippet） |
| P0 | ReAct 智能体 | 能调用工具、受最大步数约束、输出可审计的执行轨迹 |
| P0 | DAG 工作流 | 拓扑排序执行；环/重复 id/缺失依赖均报错 |
| P0 | 会话记忆 | 读写、关键词召回、按会话隔离、SQLite 落盘 |
| P0 | REST API 与控制台 | OpenAPI 3.0 可用；控制台覆盖上述能力 |
| P1 | 本地 GGUF 推理 | 配置路径即可加载，CPU 可跑 |
| P1 | 一键部署 | docker compose 一键起，双容器 healthy |

## 3. 明确不做（Out-of-Scope）

| 不做 | 原因 | 何时考虑 |
|------|------|----------|
| 用户注册/登录与权限体系 | MVP 聚焦 AI 能力，不含账号体系 | 有真实多租户需求时 |
| 分布式向量库（Qdrant 集群等） | CPU 单机即可满足 MVP，增加运维负担 | 数据量超百万片段时 |
| 多模态（图像/语音）输入 | 超出当前范围 | v2.0 |
| 模型微调 / 训练 | 定位是推理与编排中台 | 有专属数据需求时 |
| 计费与配额 | 无账号体系支撑 | 商业化阶段 |

## 4. 技术架构（版本锁定）

| 层 | 技术 | 锁定版本 | 理由 |
|----|------|----------|------|
| 服务框架 | FastAPI | 0.141.1 | 自动 OpenAPI、异步 |
| ASGI 服务器 | Uvicorn | 0.53.0 | 轻量高性能 |
| 数据契约 | Pydantic | 2.13.5 | 类型安全 |
| 向量检索 | faiss-cpu | 1.15.0 | Meta 官方，CPU 可跑 |
| 嵌入 | fastembed | 0.8.0 | ONNX，免 torch |
| 稀疏检索 | rank-bm25 | 0.2.2 | 轻量，与稠密互补 |
| 本地推理 | llama-cpp-python | 0.3.19 | llama.cpp 官方绑定 |
| 文档解析 | pypdf | 6.18.1 | 纯 Python |
| 日志 | loguru | 0.7.3 | 开箱即用 |
| 前端 | React + Vite + TS | 18.3 / 6.x / 5.7 | 轻量可维护 |

完整锁定清单：`backend/requirements.lock.txt`（逐版本 pin）。

## 5. API 端点清单（锁定）

| Method | Path | 功能 |
|--------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/v1/stats` | 系统自描述 |
| GET | `/v1/models` | 可用模型 |
| POST | `/v1/chat` | 对话（可选 RAG） |
| POST | `/v1/rag/ingest` | 文本入库 |
| POST | `/v1/rag/ingest-file` | 文件入库 |
| POST | `/v1/rag/search` | 混合检索 |
| POST | `/v1/rag/ask` | 溯源问答 |
| POST | `/v1/agent/run` | ReAct 智能体 |
| POST | `/v1/workflow/run` | DAG 工作流 |
| GET/POST/DELETE | `/v1/memory/{session}` | 记忆读写与清空 |
| POST | `/v1/memory/{session}/recall` | 记忆召回 |

## 6. 数据模型（锁定）

| 存储 | 内容 | 落盘 |
|------|------|------|
| FAISS 索引 | 向量 + 文本 + 元数据 | `data/index/faiss.index` + `meta.json` |
| SQLite | 会话消息（session/role/content/kind/ts） | `data/memory/memory.db` |

## 7. 页面清单（锁定）

| 页面 | 路由 | 依赖 API |
|------|------|----------|
| 对话 | `/`（chat） | `/v1/chat` |
| 知识库 | knowledge | `/v1/rag/*` |
| 智能体 | agent | `/v1/agent/run` |
| 工作流 | workflow | `/v1/workflow/run` |
| 系统状态 | system | `/health`、`/v1/stats`、`/v1/models` |

## 8. 设计 Token（锁定）

- 主色：青绿 `#0f766e`（纯色，不使用渐变）
- 中性：石墨系 `#f6f7f9` / `#ffffff` / `#111827`
- 字体：system-ui + Noto Sans SC
- 图标：lucide-react 描边 SVG（16/20/24px），**全项目不使用 emoji 作为功能图标**
- 主题：浅色

## 9. 验收标准（EARS 格式）

| 编号 | 功能 | 验收标准 | 优先级 |
|------|------|----------|--------|
| AC-01 | 入库 | When 提交非空文本，系统**必须**返回 doc_id 与 n_chunks 且 chunks>0 | P0 |
| AC-02 | 入库 | If 文本为空，系统**必须**返回 400 + `bad_request` | P0 |
| AC-03 | 检索 | When 知识库非空且查询非空，系统**必须**返回按分数降序的命中列表 | P0 |
| AC-04 | 问答 | When 生成答案，系统**必须**同时返回 sources 且不为空（有命中时） | P0 |
| AC-05 | 网关 | If 首选 provider 抛出异常，系统**必须**自动尝试下一 provider | P0 |
| AC-06 | 智能体 | While 步数未达上限且未输出 Final Answer，系统**必须**继续执行工具调用 | P0 |
| AC-07 | 智能体 | If 达到最大步数仍未结束，系统**必须**返回 finished=false | P0 |
| AC-08 | 工作流 | If 节点依赖成环，系统**必须**返回 400 + `workflow_error` | P0 |
| AC-09 | 记忆 | When 写入会话消息，系统**必须**能按 session 隔离读回 | P0 |
| AC-10 | 嵌入 | When 对同一文本重复嵌入，系统**必须**返回完全相同的向量 | P0 |
| AC-11 | 部署 | When 执行 docker compose up，两个容器**必须**达到 healthy | P1 |
| AC-12 | 离线 | While 无 API Key、无网络，系统**必须**仍能完成入库→检索→应答 | P0 |

## 10. 边界与约束

- 不支持 IE；响应式断点兼顾 1280 与 1440 宽屏
- 单文件代码不超过 300 行；依赖只允许向下（routes → 服务 → 网关）
- 单次上传文件上限 20 MB
- 智能体最大步数上限 12（默认 6）

## 11. 已知坑与修法

| 坑 | 根因 | 修法 |
|----|------|------|
| `zip()` 触发 ruff B905 | Python 3.10+ 要求显式 strict | 显式传 `strict=False` |
| Windows 沙箱内 esbuild/rollup postinstall 失败 | 安装脚本无法 spawn node | 用 `--ignore-scripts`，并显式补装平台原生包 |
| pnpm 注册表被劫持到 ohpm | 环境 registry 配置异常 | 显式指定 `--registry=https://registry.npmmirror.com` |
| 上传文件溯源名丢失 | 用临时文件路径取 name | 显式传入原始 `file.filename` |
| 降级链出现重复兜底实现 | 分支与末尾各追加一次 | 追加前检查 `isinstance` |
| `pywin32` 进入依赖锁 | 锁文件在 Windows 生成 | 从 lock 中剔除，保证 Linux 可安装 |

## 12. 端到端验证步骤

```bash
# 1. 安装
pip install -r backend/requirements.lock.txt

# 2. 启动
cd backend && python -m uvicorn app.api.main:app --port 8000 &

# 3. 核心成功流
curl -X POST localhost:8000/v1/rag/ingest -H "Content-Type: application/json" \
  -d '{"text":"NexusAI 由五个模块组成。","source":"a.md"}'
# 断言：200 + n_chunks>=1

curl -X POST localhost:8000/v1/rag/ask -H "Content-Type: application/json" \
  -d '{"question":"NexusAI 由几个模块组成？"}'
# 断言：200 + sources 非空

# 4. 关键错误流
curl -X POST localhost:8000/v1/workflow/run -H "Content-Type: application/json" \
  -d '{"input":"","nodes":[{"id":"a","kind":"transform","depends_on":["b"]},{"id":"b","kind":"transform","depends_on":["a"]}]}'
# 断言：400 + code=workflow_error

# 5. 测试门禁
cd backend && python -m pytest tests -q     # 断言：全部通过
python -m ruff check .                       # 断言：零告警
```

## 13. 变更记录

| 日期 | 变更 | 原因 | 影响 |
|------|------|------|------|
| 2026-09-23 | v1.0.0 初版 | MVP 交付 | 全部模块 |
