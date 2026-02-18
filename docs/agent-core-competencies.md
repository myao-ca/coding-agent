# Agent 开发核心竞争力

这份文档记录 Agent 开发的核心竞争力领域，供学习和深入研究参考。

---

## 核心竞争力一览

| 编号 | 核心竞争力 | 说明 | 深入方向 |
|------|-----------|------|----------|
| ① | **Context Management** | 上下文管理 | 压缩策略、总结算法、滑动窗口、相关性筛选 |
| ② | **Tool Design** | 工具设计 | Schema 设计、粒度控制、描述清晰度、参数校验 |
| ③ | **Prompt Engineering** | 提示词工程 | System prompt 设计、减少幻觉、行为引导 |
| ④ | **Error Handling & Recovery** | 错误处理与恢复 | 重试策略、降级方案、异常分类、自愈机制 |
| ⑤ | **Planning & Reasoning** | 规划与推理 | ReAct、Chain-of-Thought、任务分解、多步规划 |
| ⑥ | **Memory Systems** | 记忆系统 | 短期记忆、长期记忆、向量数据库、知识图谱 |
| ⑦ | **Agentic Loop Design** | 循环设计 | 终止条件、死循环检测、最大轮次、超时机制 |
| ⑧ | **Cost & Latency** | 成本与延迟优化 | 并行调用、模型选择、缓存策略、token 优化 |
| ⑨ | **Safety & Guardrails** | 安全护栏 | 危险操作拦截、权限控制、输出过滤、审计日志 |
| ⑩ | **User Experience** | 用户体验 | 流式输出、进度反馈、可中断、透明度、可解释性 |

---

## 详细说明

### ① Context Management (上下文管理)

**问题**：LLM 无状态，每次调用需传完整历史，导致 token 累积。

**策略**：
- 截断：丢弃最早的对话
- 总结：让 LLM 压缩历史对话
- 选择性保留：只保留关键信息
- 滑动窗口：保留最近 N 轮

**深入研究**：
- MemGPT 论文
- LangChain 的 ConversationSummaryMemory

---

### ② Tool Design (工具设计)

**问题**：工具设计影响 LLM 能否正确理解和使用。

**要点**：
- 名称：动词开头，清晰表达功能 (read_file, execute_code)
- 描述：说明用途、适用场景、限制
- 参数：类型明确，有默认值，有示例
- 粒度：不要太大（一个工具做太多事）也不要太小（调用太频繁）

---

### ③ Prompt Engineering (提示词工程)

**问题**：System prompt 决定 Agent 的行为模式。

**要点**：
- 明确角色和能力边界
- 规定何时使用工具、何时直接回答
- 输出格式要求
- 错误情况处理指导

---

### ④ Error Handling & Recovery (错误处理与恢复)

**问题**：工具可能失败，LLM 可能输出异常。

**策略**：
- 重试：临时性错误（网络超时）
- 降级：换个方式完成任务
- 上报：无法恢复时告知用户
- 自愈：从错误状态恢复继续执行

---

### ⑤ Planning & Reasoning (规划与推理)

**问题**：复杂任务需要先规划再执行。

**方法**：
- ReAct：Reasoning + Acting 交替
- Plan-and-Execute：先生成完整计划，再逐步执行
- Tree-of-Thought：探索多个推理路径

---

### ⑥ Memory Systems (记忆系统)

**分类**：
- 短期记忆：当前对话历史
- 长期记忆：跨会话持久化（用户偏好、项目知识）
- 外部记忆：向量数据库、知识图谱

**深入研究**：
- RAG (Retrieval Augmented Generation)
- 向量数据库 (Pinecone, Chroma, Milvus)

---

### ⑦ Agentic Loop Design (循环设计)

**问题**：Agent 循环需要正确终止，避免死循环。

**要点**：
- 最大轮次限制 (max_turns)
- 超时机制 (timeout)
- 死循环检测（重复相同操作）
- 优雅退出（保存进度）

---

### ⑧ Cost & Latency (成本与延迟优化)

**策略**：
- 并行工具调用
- 选择合适模型（简单任务用小模型）
- 缓存（相同输入不重复调用）
- 减少不必要的信息传输

---

### ⑨ Safety & Guardrails (安全护栏)

**风险**：
- 删除重要文件
- 泄露敏感信息（API Key）
- 无限循环烧钱
- 执行恶意代码

**防护**：
- 危险操作确认
- 敏感信息过滤
- 费用上限
- 沙箱执行

---

### ⑩ User Experience (用户体验)

**要点**：
- 流式输出：边生成边显示
- 进度反馈：让用户知道在做什么
- 可中断：用户可以随时停止
- 透明度：展示 Agent 的思考过程
- 可解释性：解释为什么这样做

---

## 学习进度追踪

在学习过程中，每个核心竞争力的涉及情况：

| 编号 | 核心竞争力 | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 | Step 6 | Step 7 |
|------|-----------|--------|--------|--------|--------|--------|--------|--------|
| ① | Context Management | 简陋 | 简陋 | | | | | |
| ② | Tool Design | 涉及 | 涉及 | | | | | |
| ③ | Prompt Engineering | 简陋 | 简陋 | | | | | |
| ④ | Error Handling | | | | | | | |
| ⑤ | Planning & Reasoning | | | | | | | |
| ⑥ | Memory Systems | | | | | | | |
| ⑦ | Agentic Loop Design | | 涉及 | | | | | |
| ⑧ | Cost & Latency | | | | | | | |
| ⑨ | Safety & Guardrails | | | | | | | |
| ⑩ | User Experience | | | | | | | |

---

## 各 Step 学习内容总结

### Step 1: 最小可运行的 Agent

**目标**：从零搭建一个能调用工具的 Agent，理解 Tool Use 的完整流程。

**实现了什么**：
- 创建 Agent 类，调用 Claude API（`client.messages.create`）
- 定义第一个工具 `read_file`（schema + 实现函数）
- 处理 LLM 的响应：判断 `stop_reason` 是 `end_turn`（直接回答）还是 `tool_use`（需要调用工具）
- 执行工具后，将结果以 `tool_result` 格式返回给 LLM，让它生成最终回答

**关键概念**：
- Tool Use 的工作流程：用户提问 → LLM → 调用工具 → 结果喂回 LLM → 最终回答
- `messages` 队列：LLM 无状态，每次调用必须传完整对话历史
- `response` 是结构化对象（不是字符串），包含 `stop_reason`、`content`（TextBlock / ToolUseBlock）等字段
- LLM 底层只输出 token 序列，API 层负责 serialize/deserialize

**局限**：只能处理一次工具调用，如果 LLM 需要连续调用多个工具就不行了。

---

### Step 2: Agent 循环（Agentic Loop）

**目标**：支持多轮工具调用，让 Agent 能处理更复杂的任务。

**在 Step 1 基础上扩展了什么**：
- 将单次调用改为 `while` 循环：只要 `stop_reason == "tool_use"`，就继续执行工具并回到 LLM
- 添加 `max_turns` 参数，防止无限循环
- 将 `_handle_tool_use` 改为 `_process_tool_calls`，不再直接返回结果，而是更新 messages 后继续循环

**关键概念**：
- 两层循环各司其职：
  - 外层 while 循环（⭐ 核心竞争力）：控制多轮 LLM 调用，决定何时终止
  - 内层 for 循环（纯工程实现）：遍历一次响应中的多个 tool_use
- LLM 可能一次返回多个 tool_use（并行），也可能分多次返回（串行），这是概率性的，可以通过 prompt 引导但无法 100% 控制
- `temperature` 参数控制 LLM 输出的随机性

**局限**：添加新工具需要手动改多处代码，容易遗漏。

---

## 现在实现 vs 现实对比 (Step 1-2)

### ③ Prompt Engineering

**现在的实现**：简单几行字

**现实中要考虑**：
- 引导 LLM 并行调用工具 → 提高效率
- 规定输出格式 → 减少解析错误
- 限制行为边界 → 安全
- 处理异常情况的指导 → 鲁棒性

### ① Context Management

**现在的实现**：messages 简单叠加，越来越长

**现实中要考虑**：
- 超过最大 context → 直接报错
- token 成本 → 费用爆炸
- 压缩/截断 → 可能丢失关键信息
- 什么该保留、什么该丢弃 → 影响回答质量

### ⑦ Agentic Loop Design

**现在的实现**：while 循环 + max_turns 限制

**现实中要考虑**：
- 超时机制 → 防止卡死
- 死循环检测 → 重复相同操作时终止
- 费用限制 → 烧钱上限
- 优雅中断 → 用户可以随时停止

### ② Tool Design

**现在的实现**：一个 read_file 工具，schema 写得还行

**现实中要考虑**：
- 描述是否足够清晰 → LLM 能否正确理解何时用
- 粒度是否合适 → 太大太小都不好
- 参数设计 → 类型、必填/可选、默认值
- 错误返回 → 失败时返回什么信息

---

## Tips & 知识点

### API 调用链路：从你的代码到 LLM

调用 `client.messages.create(system=..., tools=..., messages=...)` 时，实际发生的是：

1. **你传入结构化参数**（system, tools, messages 各自独立）
2. **API 服务层按内部模板拼接**成一个长 token 序列（模板不公开，和训练配套）
3. **LLM 收到的就是一个 token 序列**，它不知道什么是 API 参数

### "兼容 OpenAI API" 是什么意思？

- **只是接口格式一样**（相同的参数名、HTTP endpoint、返回格式）
- **不包括内部拼接模板**（各家模型训练不同，拼接方式也不同）
- 好处：开发者换一行 `base_url` 就能切换供应商

Anthropic 有自己的 API 设计，**不兼容 OpenAI 格式**。如果想用 OpenAI 格式调 Claude，需要中间层：

```
你的代码 (OpenAI 格式) → 中间层翻译 → Anthropic API → Claude 模型
```

现成的中间层：OpenRouter、LiteLLM。本质就是把两边 API 文档对着看，做字段映射。

### 各家 API 模板公开吗？

| 类型 | 模板是否公开 |
|------|------------|
| 闭源模型（Claude, GPT） | 不公开 |
| 开源模型（Llama, Mistral） | 公开（部署时必须知道） |

---

*文档更新于 Agent 学习项目 Step 2 阶段*
