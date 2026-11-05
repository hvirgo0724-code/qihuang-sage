# 岐黄智诊 · 中医智能诊疗协同平台

面向中医师与患者的一体化中医药 AI 辅助诊疗平台。以 LangGraph 编排的多智能体流水线为核心，融合中医知识图谱（Neo4j）、向量语义检索（Milvus）、PostgreSQL 业务记忆与 LangGraph 智能体状态图，覆盖望闻问切四诊合参、辨证论治、人工接诊审核、长期健康档案、知识浏览与运营评测的完整业务闭环。

> 注意：本系统为**辅助诊疗工具**，所有 AI 输出均标注"仅供科普、仅供参考"，不替代执业医师诊断。急危重症（胸痛、呼吸困难、意识障碍、高热惊厥、急性剧烈腹痛、大出血、孕产妇急症、自伤自杀）立即触发安全熔断并引导线下就医。

## 核心能力

| 模块 | 说明 |
| --- | --- |
| 问诊四诊合参 | 患者端 SSE 流式对话，望诊（舌象/面色）自动识别 + 十问歌结构化追问，槽位化聚合四诊证据 |
| 辨证论治 | LangGraph 三节点图检索 → 辨证 → 论治，融合 Neo4j Cypher + Milvus 向量双路 GraphRAG |
| 多通道实体抽取 | AC 自动机精确匹配图谱症状字典 + rapidfuzz 模糊兜底，按长度去重叠 + 别名对齐 |
| 症状反查兜底 | 识别症状不足时，沿候选证型反向拉取关联症状扩充检索候选集 |
| 表驱动意图路由 | 问诊流内 `IntentSpec` dataclass 声明式意图匹配，关键字长度降序避免子串误命中 |
| Prompt 三重防幻觉 | XML 指令层 + 提示层空值兜底 + 注意层重复强调，LLM 输出强制结构化 JSON |
| 人工接诊协同 | 医生端接收患者授权，审核 AI 辨证报告、编辑修订、确认发布，支持消息互动与审阅意见 |
| 长期健康档案 | PostgreSQL 事务级 advisory lock + AES-GCM 字段加密，患者明确确认的事实长期保存 |
| 知识库浏览 | 方剂/中药/证型/症状四类节点详情与邻居图谱，支持搜索、分页、图谱可视化 |
| 运营评测中心 | 提示词版本管理 + 激活、评测数据集、离线运行、准确率/召回率指标 |
| 可观测性 | OpenTelemetry + Jaeger 全链路追踪、Prometheus + Grafana 多面板、LangSmith 模型级追踪 |

## 技术栈

**后端** Python 3.11 / FastAPI / LangChain 1.x / LangGraph 1.x / SQLAlchemy 2 / asyncio + uvicorn / Celery + Redis / structlog

**AI 与 RAG** Neo4j 图数据库（知识图谱）+ Milvus 向量数据库 / 图谱-向量融合 GraphRAG / AC 自动机 + rapidfuzz NER / 多模型降级（主模型故障时自动切换）/ LLM 调用安全护栏

**数据库与存储** MySQL（业务库：用户、会话、消息、审计）/ PostgreSQL（智能体长期记忆 + 结构化槽位快照）/ Redis（会话状态、Celery broker、槽位暂存）/ S3（对象存储：上传图像、评测数据集）

**前端** Vue 3 + Vite 5 + TypeScript + Element Plus 2 / Pinia / Vue Router 4 / ECharts（知识图谱可视化）/ Axios（带 token 自动刷新 + 401 统一拦截）

**容器与可观测性** Docker Compose 单机部署基线 / Prometheus + Grafana / Jaeger（OTLP gRPC 接收）/ OpenTelemetry Python 全栈埋点

## 快速启动

前置：Docker Desktop 4.88+，WSL2 后端建议开启至少 6 GB 内存、30 GB 磁盘。

```powershell
# 1. 克隆项目
git clone <你的仓库地址> qihuang-sage
cd qihuang-sage

# 2. 配置
#   .env.example 中 JWT_SECRET_KEY 与 ENCRYPTION_KEY 是占位值，
#   生产部署必须替换。开发环境可直接用默认值启动。
Copy-Item .env.example .env

# 3. 启动全栈
docker compose up -d --build

# 4. 验证
Invoke-RestMethod http://localhost:8000/healthz
# {"status":"ok","version":"1.0.0"}

# 5. 登录
#   管理员  admin / admin123
#   医生在 /admin/doctors 页面创建
#   患者在 /login 注册
```

默认暴露端口：80（前端）/ 8000（后端）/ 3000（Grafana）/ 16686（Jaeger）/ 9090（Prometheus）。

## 架构总览

```
        ┌───────────────────────┐
        │  患者端 / 医生端 / 管理端  │   Vue 3 + Vite + Element Plus
        └──────────┬────────────┘
                   │ /api/v1  ──>  http://localhost:8000
        ┌──────────▼────────────┐
        │      FastAPI Router     │   auth / consultation / knowledge /
        └──────────┬────────────┘   clinical / admin / observatory ...
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
LangGraph    业务服务层    安全护栏
  三节点诊断    (NER / 记忆   (prompt 三重锁 /
 retrieve →   合并 / 数据    急危重症熔断 /
 differentiate 导出)        确定性 JSON 输出)
   recommend
     │
     ├─▶ Neo4j 知识图谱  (Cypher 参数化查询)
     ├─▶ Milvus 向量库   (相似度搜索 + 重排)
     ├─▶ PostgreSQL 记忆 (advisory lock + AES-GCM)
     ├─▶ MySQL 业务库    (用户、会话、消息、审计)
     └─▶ Redis + Celery  (任务队列、图像识别异步任务)
```

### RAG 流水线（实体抽取 → 图谱检索 → 向量检索 → 辨证）

```
自由文本问诊消息
    │
    ▼
多通道实体抽取 (app/services/ner.py)
    ├─ 通道 A：AC 自动机（图谱症状字典 + aliases → 标准名）
    ├─ 通道 B：rapidfuzz 模糊兜底（未命中片段的 Top-1 匹配）
    ├─ 长度降序去重叠（"盗汗"不会被"出汗"截断）
    └─ 别名 → 标准名归一化（"怕冷" → "恶寒"）
    │
    ▼
症状反查兜底 (knowledge_service.graphrag_retrieve)
    ├─ 识别症状 ≤ 2 个时：取 top-3 候选证型 → 反查所有关联症状
    └─ 用扩充后的症状列表重跑症状 → 证型检索，拿更全候选
    │
    ▼
图谱 + 向量双路检索
    ├─ Neo4j：症状 ─MANIFESTS─▶ 证型 ─TREATS─▶ 方剂 ─CONTAINS─▶ 中药
    └─ Milvus：主诉/兼症 embedding → Top-K 证型/方剂/中药语义相似度
    │
    ▼
LangGraph 辨证图 (retrieve → differentiate → recommend)
    └─ Prompt 三重防幻觉：<指令> + <提示> 空值兜底 + <注意> 强调
```

### 意图路由（问诊流内）

问诊流内的追问继续 / 触发报告 / 结束问诊 / 紧急情况由 `consultation_service._route_intent` 表驱动：

- `_INTENT_SPECS` 每个 spec 声明 `(关键字组, 动作)`
- 遍历顺序按 spec 内最长关键字长度降序，"生成报告" 不会被 "报告" 子串误命中
- 触发报告生成后，若槽位已足够（ready=true），LangGraph 诊断图立即启动

### 安全护栏

| 层 | 机制 |
| --- | --- |
| 急危重症熔断 | 安全服务匹配胸痛/呼吸困难/意识障碍等关键词 → 直接跳转线下就医页面 |
| Prompt 三重锁 | XML `<指令>` + `<提示>` 空值兜底 + `<注意>` 重复强调 |
| Cypher 参数化 | 所有 Neo4j 查询使用 `$param` 占位符，f-string 仅用于标签名/关系类型 |
| JSON Schema 输出 | Pydantic 强制 LLM 输出为严格 JSON，解析失败自动重试 |
| 预算有界 | `BoundedToolExecutor` 每个角色独立 16 次工具调用上限 + 未绑定工具抛 PermissionError |
| 数据加密 | PostgreSQL 长期记忆 AES-GCM 字段加密，ENCRYPTION_KEY 统一配置 |

## 目录结构

```
qihuang-sage/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI 路由（auth / consultation / knowledge / clinical / admin ...）
│   │   ├── core/             # 基础设施（graph / neo4j_client / milvus_client / metrics / settings / security）
│   │   ├── models/           # SQLAlchemy + Neo4j 实体定义
│   │   ├── schemas/          # Pydantic 输入/输出模型
│   │   ├── services/         # 业务层：consultation / knowledge / syndrome / prompt / ner / safety ...
│   │   └── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/              # axios http client + 业务接口
│   │   ├── router/           # Vue Router（含路由级权限守卫）
│   │   ├── views/            # 页面组件（Patient / Doctor / Admin）
│   │   ├── components/       # 通用组件（Bubble / HumanConsultation / DoctorReportEditor / KnowledgeGraph ...）
│   │   ├── stores/           # Pinia stores
│   │   └── App.vue
│   ├── Dockerfile            # 多阶段：node build → nginx serve
│   └── nginx.conf            # SPA fallback + /api /healthz 反向代理
├── docker-compose.yml        # 单机部署基线
├── .env.example
├── docs/                     # 开发与运维文档
└── README.md
```

## API 速览

| 路由前缀 | 角色 | 说明 |
| --- | --- | --- |
| `/api/v1/auth/*` | 全部 | 注册 / 登录 / 刷新 / 注销 / 个人信息 / 数据导出与注销 |
| `/api/v1/consultation/*` | 患者 | 会话 CRUD / 图片上传 / 多轮 SSE 对话 / 辨证报告 / 历史列表 |
| `/api/v1/knowledge/*` | 患者 | 搜索 / 方剂中药证型症状四类节点详情 |
| `/api/v1/clinical/*` | 患者 / 医生 | 申请 / 接受 / 消息 / 审核 / 报告编辑确认 / 结束 / 取消 |
| `/api/v1/memory/*` | 患者 | 长期记忆 CRUD + 核实候选 |
| `/api/v1/admin/*` | 管理员 | 医生管理 / 提示词版本 / 评测数据集 / 图谱统计 / 审计与操作日志 |
| `/healthz` | 公开 | 健康检查（nginx 透传，监控页用） |
| `/readyz` | 公开 | 深度就绪检查（含 MySQL / PostgreSQL / Redis / Neo4j / Milvus / S3） |
| `/metrics` | 公开 | Prometheus 指标（tcm_requests_total / tcm_llm_latency_seconds ...） |
| `/api/docs` | 公开 | Swagger UI |

### 示例：多轮 SSE 对话

```powershell
# 登录拿 token
$login = Invoke-RestMethod 'http://localhost:8000/api/v1/auth/login' `
  -Method Post -ContentType 'application/json' `
  -Body '{"username":"patient093413","password":"PatientPass1234"}'

# 创建会话
$sess = Invoke-RestMethod 'http://localhost:8000/api/v1/consultation/session' `
  -Method Post -ContentType 'application/json' -Headers @{Authorization="Bearer $($login.access_token)"} `
  -Body '{"complaint":"近一月乏力、饭后腹胀"}'

# 流式问诊（curl 支持 -N 不缓冲）
curl -N -X POST "http://localhost:8000/api/v1/consultation/$($sess.session_id)/chat" `
  -H "Authorization: Bearer $($login.access_token)" `
  -H "Content-Type: application/json; charset=utf-8" `
  -d '{"message":"最近总觉得没力气，吃完饭肚子胀，大便偏稀。"}'
```

SSE 事件类型：`token`（流式 token）/ `slot`（槽位更新）/ `button`（按钮选项）/ `system`（系统提示）/ `result`（辨证报告已生成）/ `error`（错误）。

## 开发规范

- **Docker-first**：改动后端后必须 `docker compose build backend && docker compose up -d --force-recreate backend`；前端同理。
- **Cypher 参数化**：新增 Neo4j 查询必须使用 `$param` 占位符；标签名/关系类型是代码常量，不能拼自用户输入。
- **Prompt 版本化**：所有 scene 的 prompt 模板走 `prompt_service.get_active_prompt(scene)`，默认值写在 `prompt_service.DEFAULT_PROMPTS`，上线后以 DB prompt_version 表为准。
- **Pydantic 优先**：所有输入/输出都定义 schema；外部 SSE 输出使用 `message_type` + `meta` 字典而非裸文本。
- **日志与追踪**：业务异常统一用 structlog；HTTP handler 返回 `X-Trace-Id` 响应头；Jaeger UI 16686 按 trace_id 检索。
- **安全护栏不可绕过**：`BoundedToolExecutor`、安全服务、JSON Schema 校验都在编排层强制执行，不可在工具内部自行跳过。

## 生产部署清单

- [ ] 替换 `.env` 中 JWT_SECRET_KEY / ENCRYPTION_KEY / ADMIN_PASSWORD / CORS_ORIGINS
- [ ] APP_ENV=production，关闭 OpenAPI 文档对外暴露
- [ ] 镜像锁定 digest、启用漏洞扫描
- [ ] PostgreSQL 定期备份（pg_dump）与恢复演练
- [ ] S3Mock → 正式对象存储；Jaeger all-in-one → 持久化后端
- [ ] Prometheus 抓取配置、Grafana 告警路由
- [ ] 容量与压测（至少 500 并发问诊会话）
- [ ] TLS 终止（nginx 反代层）、密钥轮换流程

## 验证

详细回归命令与故障排查见 [部署更新与故障排查](docs/部署更新与故障排查.md)。

```powershell
# 一键回归（Docker 需在运行）
docker compose ps -a                  # 所有容器 healthy
Invoke-RestMethod http://localhost:8000/readyz
# {"status":"ok","dependencies":{"mysql":true,"postgresql":true,"redis":true,"neo4j":true,"milvus":true,"s3":true}}
```
