# LangGraph 教学大纲

> 面向对象：有后端/Go 经验、正在用百度 SEDA（dh-agent-core）做数字人 Agent 的学习者。
> 教学方式：**每次只讲一个知识点**，确认掌握后再进入下一讲；尽量结合你的 SEDA 框架做对照。
> 代码位置：每讲一个独立目录，示例可直接运行。

## 进度图例

✅ 已讲完　🔵 进行中　⬜ 待讲

## 如何使用本大纲

1. 按顺序往下走，一讲一个知识点。
2. 每讲结束我会出一道小检查题，你答完/跑通再进下一讲。
3. 想跳讲或回看也可以，直接告诉我讲次编号。

---

## 第一阶段 · 基础篇（搞懂图怎么搭、状态怎么流）

| 讲次 | 目录 | 知识点 | 一句话目标 | 状态 |
|------|------|--------|-----------|------|
| 1 | （纯概念） | LangGraph 是什么 | 理解 节点/边/状态 三件套，知道它解决"循环+分支+记忆" | ✅ |
| 2 | `01_hello_graph/` | 第一个图 StateGraph | 用 2 节点 1 边跑通，理解 add_node/add_edge/compile/invoke | ✅ |
| 3 | `02_state_reducer/` | State 深入 | 搞懂状态"合并"语义：默认覆盖 vs `Annotated`+reducer 追加 | ✅ |
| 4 | `03_conditional_edge/` | 条件边 | 用路由函数根据运行结果决定走哪条分支（对照你的 condition 返回码） | ✅ |
| 5 | `04_loop/` | 循环 | 条件边指回旧节点形成 loop，用 recursion_limit 兜底（对照成环边） | ✅ |

---

## 第二阶段 · 进阶篇（并行、动态、接入大模型）

| 讲次 | 目录 | 知识点 | 一句话目标 | 状态 |
|------|------|--------|-----------|------|
| 6 | `05_parallel/` | 并行 fan-out/fan-in | 一个节点分叉出多个并行节点再汇聚，理解超步 + barrier + reducer 合并 | ✅ |
| 7 | `06_send_api/` | Send 动态并行 | 用 `Send` 在运行时动态派发 N 个并行任务（map-reduce 模式） | ✅ |
| 8 | `07_first_llm/` | 节点里调大模型 | 第一次在节点中接入 LLM，把"函数节点"升级成"智能节点" | ✅ |
| 9 | `08_tool_calling/` | 工具调用 | 用 ToolNode 让模型调工具（对照你的 toolregistry / web_search） | ✅ |
| 10 | `09_react_agent/` | ReAct Agent | 用 prebuilt `create_react_agent` 搭一个会"思考-调工具-再思考"的智能体 | ✅ |

---

## 第三阶段 · 高级篇（记忆、人机协作、流式、子图）

| 讲次 | 目录 | 知识点 | 一句话目标 | 状态 |
|------|------|--------|-----------|------|
| 11 | `10_checkpointer/` | 持久化记忆 | 用 Checkpointer 让图能记住多轮对话、支持断点续跑 | ✅ |
| 12 | `11_human_in_loop/` | 人机协作 | 用 `interrupt` 暂停图、等人工确认后再继续 | ✅ |
| 13 | `12_streaming/` | 流式输出 | 用 `stream`/`astream_events` 边算边吐（对照你的 SSE + streamproc） | ✅ |
| 14 | `13_subgraph/` | 子图 | 把一张图当作另一张图的一个节点，分层组织复杂流程 | ✅ |

---

## 第四阶段 · 实战篇（把知识串起来）

| 讲次 | 目录 | 知识点 | 一句话目标 | 状态 |
|------|------|--------|-----------|------|
| 15 | `14_capstone/` | 综合实战 | 用 LangGraph 复刻一个**简化版数字人对话流**（意图判断→并行工具→汇聚回复） | ✅ |
| 16 | `LANGGRAPH_VS_SEDA.md` | LangGraph vs SEDA | 两套架构的终极对比：各自强项、何时选哪个 | ✅ |

---

## 你已经问过、后续会重点展开的问题

学到对应讲次时，我会专门回头把这些讲透：

- **多边并行 + 一路命中打断其他路**？→ 第 6 讲（并行）+ 第 15 讲（实战）会对比 SEDA 的 `UseToolSignalChan` 抢占式取消，讲清 LangGraph 为什么默认做不到、要怎么绕。
- **条件分支到底怎么选路**？→ 第 4 讲（条件边）。
- **流式吐字怎么实现**？→ 第 13 讲（streaming），对照你的 `streamproc` + SSE。

---

## 运行环境备忘

- 依赖用 **uv** 自行安装（你来装）。装好后两种跑法：
  - 项目模式：`uv run python 01_hello_graph/hello_graph.py`（推荐，自动管环境、绕开 python alias 坑）
  - 或传统：`.venv/bin/python 01_hello_graph/hello_graph.py`
- ⚠️ 本机 zsh 把 `python` 别名指向系统 `/usr/bin/python3`，**别直接敲 `python xxx.py`**，会找不到 langgraph。
