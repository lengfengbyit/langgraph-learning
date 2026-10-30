# LangGraph 学习笔记

从零学习 LangGraph 的示例代码仓库。每一讲一个独立目录，由浅入深。

## 环境配置（第一次使用）

```bash
cd langgraph-learning
python3 -m venv .venv            # 创建虚拟环境（隔离依赖，不污染系统 Python）
source .venv/bin/activate        # 激活（每次新开终端都要执行）
pip install -r requirements.txt  # 安装依赖
```

激活后终端提示符前会出现 `(.venv)`。退出用 `deactivate`。

## 运行某一讲的示例

```bash
# 推荐：直接用虚拟环境里的 python（最稳，不受 shell alias 影响）
.venv/bin/python 01_hello_graph/hello_graph.py
```

> ⚠️ 注意：本机 `zsh` 把 `python` 设了别名指向系统 `/usr/bin/python3`，
> 即使 `source .venv/bin/activate` 激活了虚拟环境，直接敲 `python xxx.py`
> 仍会用系统 Python（找不到 langgraph）。所以请用上面的 `.venv/bin/python`。

## 目录结构（随学习推进逐步新增）

| 讲次 | 目录 | 知识点 | 状态 |
|------|------|--------|------|
| 第 1 讲 | （纯概念） | 什么是 LangGraph：节点/边/状态三件套 | ✅ 已讲 |
| 第 2 讲 | `01_hello_graph/` | 用代码搭第一个图（2 节点 1 边，不调大模型） | ✅ 已讲 |
| 第 3 讲 | `02_state_reducer/` | State 深入：覆盖 vs 追加（reducer 合并语义） | ✅ 已讲 |
| 第 4 讲 | `03_conditional_edge/` | 条件边：路由函数根据结果决定走哪条分支 | ✅ 已讲 |
| 第 5 讲 | `04_loop/` | 循环：条件边指回旧节点形成 loop + recursion_limit 兜底 | ✅ 已讲 |
| 第 6 讲 | `05_parallel/` | 并行 fan-out/fan-in：超步 + barrier + reducer 合并 | ✅ 已讲 |
| 第 7 讲 | `06_send_api/` | Send API：运行时动态并行（map-reduce） | ✅ 已讲 |
| 第 8 讲 | `07_first_llm/` | 第一次在节点里调用大模型（智能节点） | ✅ 已讲 |
| 第 9 讲 | `08_tool_calling/` | 工具调用：模型自己决定调工具（Agent 核心） | ✅ 已讲 |
| 第 10 讲 | `09_react_agent/` | create_react_agent：一行封装 ReAct 智能体 | ✅ 已讲 |
| 第 11 讲 | `10_checkpointer/` | 持久化记忆：Checkpointer + thread_id 多轮对话 | ✅ 已讲 |
| 第 12 讲 | `11_human_in_loop/` | 人机协作：interrupt 暂停 + Command 恢复 | ✅ 已讲 |
| 第 13 讲 | `12_streaming/` | 流式输出：stream 边算边吐（对照 SSE + streamproc） | ✅ 已讲 |
| 第 14 讲 | `13_subgraph/` | 子图：把一整张图当作另一张图的一个节点 | ✅ 已讲 |
| 第 15 讲 | `14_capstone/` | 实战：简化版数字人对话流（综合运用） | ✅ 已讲 |
| 第 16 讲 | `LANGGRAPH_VS_SEDA.md` | 终极对比：LangGraph vs SEDA 决策表 | ✅ 已讲 |

🎉 **全部 16 讲完成！** 对比总结见 [LANGGRAPH_VS_SEDA.md](LANGGRAPH_VS_SEDA.md)，速查笔记见 [NOTES.md](NOTES.md)。

## 核心概念速查（学到哪补到哪）

- **State（状态）**：全程流动的共享"笔记本"，用 `TypedDict` 声明。
- **Node（节点）**：一个函数 `node(state) -> dict`，返回要更新进 state 的字段。
- **Edge（边）**：`add_edge(a, b)`，决定节点之间怎么走。`START`/`END` 是内置起止点。
- **compile（编译）**：把搭好的图变成可执行对象。
- **invoke（调用）**：传入初始 state，跑完整张图，返回最终 state。

## 与 SEDA（dh-agent-core）的对照

| 概念 | LangGraph | 你的 SEDA 框架 |
|------|-----------|----------------|
| 节点 | 一个函数 | `Operator` struct + `DoImpl()` |
| 边 | `add_edge` 代码 | `conf/flow/*.conf` 里的 JSON |
| 状态 | `State`(TypedDict) | `FlowContext` 黑板 |
| 并发模型 | 超步 + barrier（整齐） | goroutine + channel（自由） |
