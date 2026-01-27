# Anything2Skill 多智能体实现说明（全量方案 + 当前落地）

本文结合：
- 本项目现有代码结构（FastAPI + services + UI）
- `docs/ANY2SKILL.pdf` 的目标流程
- `docs/1.笔记/` 的多智能体工程实践

目标：先把三 Agent 闭环跑通，再逐步演进到完整体系。

---

## 一、全量方案（最全面版本，目标态）

### 1) 目标与产物
- **输入**：用户任务描述
- **输出**：可交付技能包（标准化 Skill + 测试用例 + 执行报告）

技能包包含：
- 标准化 Skill 表达（步骤、约束、依赖、输入输出、失败处理）
- 可复现测试用例
- 执行报告（通过/失败 + 原因）

### 2) 多 Agent 角色与职责
- **Orchestrator（编排器）**：
  - 只负责流程控制、路由、失败回流、终局汇总
  - 不做具体执行与检索
- **Skill 生成 Agent**：
  - 聚合检索/转写/结构化信息
  - 生成标准化 Skill
- **场景模拟 Agent**：
  - 根据任务 + Skill 生成测试用例
  - 覆盖输入、环境假设、预期结果、边界条件
- **执行器 Agent**：
  - 真实执行任务（GitHub/API/Whisper/文件生成）
  - 产出结果并回传执行报告
  - 执行失败则回流或终止

### 3) 关键设计原则（来自笔记实践）
- **中心化调度**：所有任务先交给 Orchestrator
- **专才专用**：每个 Agent 独立 Prompt 与工具
- **边界清晰**：Orchestrator 不执行，子 Agent 不越权
- **Handoff 协议**：明确 next_agent 或 final
- **状态感知**：防止踢皮球/死循环
- **可观测性**：SSE + 结构化日志

### 4) 工程能力
- **Prompt 解耦**：独立提示词文件
- **工具统一接口**：tool_registry 统一调用
- **Pydantic 强类型**：工具入参、Agent 输出结构化
- **会话记忆**：SessionManager（后续增强）

---

## 二、当前项目映射与约束（落地依据）

### 1) 已有能力（可复用）
- `src/services/llm.py`：LLM 调用与 Skill 生成
- `src/services/video_pipeline.py`：视频抽取 + Whisper 转写
- `src/services/github_search.py`：GitHub 搜索
- `src/services/skills_sh.py`：skills.sh 检索与安装
- `src/api/agent_arena.py`：SSE 流式 UI（Simple/ Augmented）
- `src/api/anything2skills.py`：搜索与生成 API

### 2) 当前限制
- 暂无 SessionManager
- 暂无统一工具注册层
- Augmented 仅是“增强检索+LLM”，非闭环

---

## 三、阶段性落地方案（当前实现）

### 1) 先实现三 Agent 闭环（不重构全目录）
- **新增目录（轻量分层）**：
  - `src/core_agents/`（三 Agent + orchestrator）
  - `src/prompts/`（独立 prompts）
  - `src/application/`（编排入口 + SSE 事件规范）
  - 保留现有 `src/services/`

### 2) 编排主流程（MVP）
1. Orchestrator → 执行器 Agent（真实执行）
2. Orchestrator → Skill 生成 Agent（基于执行结果）
3. Orchestrator → 场景模拟 Agent
4. Orchestrator → 质量验证（Validator）
5. 失败回流 → Skill 生成 Agent（最多 N 轮）
6. 成功 → 输出 执行结果 + Skill + 测试 + 报告

### 3) Handoff 与防死循环
- **强制 next_agent 或 final**
- **max_rounds**（建议 2~3 次）
- **状态感知**（连续失败直接返回用户补充信息）

### 4) 工具调用规范
- 统一封装到 `tool_registry`：
  - `skills_sh_search`
  - `github_search`
  - `video_extract`
  - `llm_generate_skill`
- Agent 只面向 `tool_name + arguments`

---

## 四、数据结构与输出规范

### 1) Agent 输出结构（建议）
```json
{
  "status": "ok|fail",
  "next_agent": "scenario_simulator|executor|final",
  "payload": {},
  "errors": [],
  "trace_id": "uuid"
}
```

### 2) SSE 事件格式
```json
{
  "agent": "skill_generator",
  "stage": "action|thought|observation|error|done",
  "event": "search|generate|validate",
  "payload": {},
  "timestamp": 1730000000
}
```

---

## 五、SSE 可观测性与日志

- SSE 由 `agent_arena` 输出到前端
- 后端同时记录结构化日志（可选）
- 关键事件包括：
  - handoff
  - tool_call
  - validation_result
  - retry

---

## 六、后续扩展路线（全量方案的补齐）

1. **SessionManager**：引入会话记忆与上下文截断
2. **Knowledge Base**：RAG 检索（参照 Chapter03/04）
3. **工具协议升级**：MCP 化工具接入
4. **自动化测试**：持续集成运行技能测试
5. **Agents SDK**：若复杂度提高可迁移
6. **在线搜索 MCP**：接入 Bocha 搜索服务，供执行器与生成器使用

---

## 七、框架选择（当前阶段）

- **编排框架**：自写编排 + 现有 LLM 调用
- **原因**：改动小、风险低、快速跑通闭环
- **未来可选**：OpenAI Agents SDK / LangChain

---

## 八、我们要实现的部分（本次落地范围）

1. 新增 `core_agents`（三 Agent + orchestrator）
2. 新增 `prompts`（独立 prompt 文件）
3. 新增 `application` 编排入口 + SSE 事件标准化
4. 新增 `tool_registry` 统一工具调用
5. 替换 Augmented 流程为“执行→生成→验证”闭环
