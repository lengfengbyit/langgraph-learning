# LangGraph 学习笔记（速查版）

> 一份从零到能搭生产级 Agent 的 LangGraph 精华笔记，16 讲浓缩。
> 配套可运行示例在同目录 `01~14` 各讲文件夹，完整大纲见 `CURRICULUM.md`，
> 框架对比见 `LANGGRAPH_VS_SEDA.md`。

## 心智模型：一切都是「图」

```
State（共享笔记本） ── 在节点间流动
  Node（函数，干活）── add_node 注册
  Edge（箭头，定向）── add_edge 连接
  compile() 定稿 → invoke()/stream() 开跑
```

一句话：**LangGraph = 用图编排 AI 工作流，擅长"循环 + 分支 + 记忆"。**

---

## 基础篇（1-5）：图怎么搭、状态怎么流

**① 节点 = 函数** `node(state) -> dict`，返回值**合并**进 state（不是替换整个 state）。

**② 边 = 连接**，`START`/`END` 是内置起止点；没有边连过去的节点不会执行。

**③ State 合并靠 reducer**（关键）：
```python
last: str                              # 默认：覆盖(last-write-wins)
history: Annotated[list, operator.add] # 配 reducer：追加/合并
```
reducer 是函数 `(旧值,新值)->合并值`。**并行写同一字段必须配 reducer,否则报 InvalidUpdateError。**

**④ 条件边 = 动态选路**：
```python
def route(state) -> str: return state["intent"]   # 只读、不改 state
builder.add_conditional_edges("node", route, {"a":"nodeA", "b":"nodeB"})
# 返回 path_map 里没有的 key → KeyError；记得留兜底分支
```

**⑤ 循环 = 条件边指回旧节点**：
```python
builder.add_conditional_edges("work", check, {"retry":"work", "done":END})
# 必须有出口判断；recursion_limit(默认25) 是防跑飞的全局刹车
# 单环次数上限需自己在 state 里计数 + 路由函数里检查
```

---

## 进阶篇（6-10）：并行、动态、接入大模型

**⑥ 并行 fan-out/fan-in**：多条边同源=并行(同一超步)，多条边同目标=汇聚(barrier 等全部完成)。
```python
builder.add_edge("dispatch", "web"); builder.add_edge("dispatch", "rag")  # fan-out
builder.add_edge("web", "join");     builder.add_edge("rag", "join")      # fan-in
```
超步内各分支**互相隔离、看不见**，状态等 barrier 后才合并 → 这是"无法跨分支实时抢占"的根因。

**⑦ Send = 运行时动态并行**（map-reduce）：
```python
def dispatch(state) -> list[Send]:
    return [Send("worker", {"item": x}) for x in state["items"]]  # 有几个派几个
builder.add_conditional_edges(START, dispatch, ["worker"])
```

**⑧ 节点里调模型**：`ChatOpenAI` + messages（`System`/`Human`/`AI`）。
```python
llm = ChatOpenAI(model="deepseek-chat", base_url="https://api.deepseek.com", api_key=...)
resp = llm.invoke([SystemMessage(...), HumanMessage(...)]); resp.content
```

**⑨ 工具调用 = Agent 核心**：
```python
@tool
def f(x: str) -> str:
    """docstring 是模型判断何时调用的依据，必须写清楚"""
llm_with_tools = llm.bind_tools([f])
builder.add_node("tools", ToolNode([f]))
builder.add_conditional_edges("agent", tools_condition)  # 有tool_calls→tools，没有→END
builder.add_edge("tools", "agent")                       # 形成 agent⇄tools 循环
```
模型只"点单"(返回 tool_calls)，**工具由 ToolNode(框架)执行**，结果回 agent 再生成答案。

**⑩ create_react_agent = 第⑨讲一行封装**：
```python
agent = create_react_agent(llm, tools=[f], prompt="系统提示")
```
标准 Agent 用它；需要定制控制流(并行/抢占/特殊状态)则手搓。

---

## 高级篇（11-14）：记忆、协作、流式、子图

**⑪ 持久记忆 Checkpointer**：
```python
graph = builder.compile(checkpointer=MemorySaver())  # 生产用 PostgresSaver
cfg = {"configurable": {"thread_id": "会话id"}}       # 同 thread_id 共享记忆
graph.invoke({...}, cfg)   # 历史自动加载，靠 add_messages reducer 拼接
```
MemorySaver(内存,退出即丢) / SqliteSaver(文件) / PostgresSaver(生产)。

**⑫ 人机协作 interrupt/Command**（依赖 checkpointer）：
```python
decision = interrupt({"question": "批准?"})   # ⏸ 图暂停，payload 抛给人
graph.invoke(Command(resume="approve"), cfg)  # 从暂停处恢复
```
⚠️ **大坑：resume 时中断节点会从头重跑**，`interrupt()` 之前别放副作用代码(扣款/写库)。

**⑬ 流式 stream**：`updates`(每节点增量) / `values`(每步全量) / `messages`(逐token打字机)。
```python
for token, meta in graph.stream({...}, stream_mode="messages"):
    print(token.content, end="")   # 攒句/解析标签等加工，自己在这层做
```
工具执行那段时间 token 流静默(非模型在生成) → 需要"垫句"填空白。

**⑭ 子图 = 一张编译图当节点**：
```python
builder.add_node("research", subgraph)   # add_node 第二参可以是另一张图
```
父子共享的 state key 自动流转；schema 不同需包装函数转换。
**模块边界要顺着耦合切**：需要互相抢占的链路应整体封装，抢占逻辑在内部实现。

---

## ⚠️ 踩坑清单（最该记住的）

1. 并行写同一字段 → 必须配 reducer，否则 `InvalidUpdateError`。
2. 条件边返回 path_map 没有的 key → `KeyError`，留兜底分支。
3. 循环忘了出口判断 → 撞 recursion_limit 抛错。
4. `interrupt()` 之前放副作用代码 → resume 时重复执行（节点重跑）。
5. 工具 `@tool` 的 docstring 写得含糊 → 模型乱调或不调。
6. 以为并行分支能互相看见/抢占 → barrier 隔离，做不到，要钻 asyncio。

---

## 🚀 最小代码模板

```python
from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    input: str
    output: Annotated[list, operator.add]

def my_node(state: State) -> dict:
    return {"output": [f"处理了 {state['input']}"]}

builder = StateGraph(State)
builder.add_node("work", my_node)
builder.add_edge(START, "work")
builder.add_edge("work", END)
graph = builder.compile()

print(graph.invoke({"input": "hello", "output": []}))
```

---

## 与 SEDA 一句话对照

**LangGraph** 轻量/代码驱动/超步并发,标准 Agent 省心;**SEDA** 工业级/配置驱动/channel 并发,实时抢占与极致并发更强。详见 `LANGGRAPH_VS_SEDA.md`。
