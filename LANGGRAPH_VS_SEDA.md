# LangGraph vs SEDA 终极对比

> 本文是 LangGraph 学习课程第 16 讲（收官总结），把前 15 讲的所有对照点收拢成
> 一张"什么场景该选哪个"的决策参考。不含新代码，是给这套知识盖个章。

## 一句话结论

**LangGraph = 轻量、代码驱动、超步(barrier)并发的图引擎；SEDA = 工业级、配置驱动、channel 自由并发的图引擎。** 两者核心三件套（节点/边/状态）完全同构，分水岭在**并发模型**和**封装度**。

---

## 一、核心范式差异

| 维度 | LangGraph | SEDA |
|------|-----------|----------------------|
| 并发模型 | Pregel/BSP：超步(superstep) + barrier 栅栏同步 | Staged Event-Driven：goroutine + channel 事件驱动 |
| 节点形态 | 一个函数 `node(state)->dict`（轻） | `Operator` struct + `DoImpl()`（重，带生命周期） |
| 搭图方式 | 写 Python 代码 `add_node/add_edge` | 写 JSON 配置 `conf/flow/*.conf` + 代码生成 |
| 并发特点 | 整齐：一批节点并行→barrier→下一批 | 自由：各 goroutine 独立跑，channel 手动协调 |

---

## 二、逐能力对照（15 讲浓缩）

| 能力 | LangGraph | SEDA | 谁更省心 |
|------|-----------|------|----------|
| 节点/边/状态 | 函数 / add_edge / TypedDict | Operator / JSON edge / FlowContext | 持平 |
| 状态合并 | reducer（`Annotated[.., add]`） | FlowContext Set(覆盖)/Push(追加) | 持平 |
| 条件分支 | 路由函数返回标签 | 算子返回码匹配 condition | 持平 |
| 循环 | 条件边指回 + recursion_limit(全局) | 成环边 + circleRunCountLimit(单环) | SEDA 更精细 |
| 动态并行 | `Send` 列表 | op_task_split 下发子任务 | 持平 |
| 工具调用 | `@tool` + ToolNode + tools_condition | toolregistry + 工具算子 + op_tool_router | 持平 |
| 标准 Agent | `create_react_agent` 一行 | 需手搓 | **LangGraph 省心** |
| 持久记忆 | Checkpointer 挂上即用，一行换后端 | op_context_manager 手工管理 | **LangGraph 省心** |
| 人机协作 | `interrupt`/`Command` 通用机制 | library/interrupt 自实现 | **LangGraph 省心** |
| 流式 | `stream` 给原始 token 流 | streamproc 攒句/解析标签/SSE | **SEDA 更贴业务** |
| 子图 | 编译图当节点 | isSubFlowOp | 持平 |
| **跨链路抢占取消** | ❌ 图层面做不到，要钻 asyncio | ✅ channel 原生一等公民 | **SEDA 完胜** |

---

## 三、那个贯穿全程的关键差异：跨链路实时抢占

- **SEDA**：goroutine 各自独立跑，一路命中 → channel 发信号 → 其他路 `select` 到立刻取消。"成功即抢占"是一等公民（`UseToolSignalChan`）。
- **LangGraph**：同一超步的并行分支被 barrier 隔离、互相看不见，所以**图层面做不到"一路命中打断其他路"**。惯用法是"都跑完，在 join 节点选赢家"（方案①，行为等价但不省算力）；真要抢占，得把竞速塞进单节点用 `asyncio.wait(FIRST_COMPLETED)`+`cancel()`（方案③）。
- **根因**：抢占需要"共享的实时信号通道"，这与超步隔离、与子图封装的"切断耦合"目标天然冲突。**模块边界要顺着耦合切**——需要互相抢占的链路应作为一个整体封装，抢占逻辑在内部实现。

---

## 四、决策表：什么场景选哪个

| 你的场景 | 推荐 | 理由 |
|----------|------|------|
| 快速搭标准 Agent（问答+工具） | **LangGraph** | `create_react_agent` 一行，生态成熟 |
| 需要多轮记忆、断点续跑、人工审批 | **LangGraph** | Checkpointer/interrupt 开箱即用 |
| 原型验证、团队不熟 Go | **LangGraph** | Python 生态、调试直观、门槛低 |
| 多路竞速 + 命中抢占取消（你的数字人） | **SEDA** | channel 抢占是刚需，LangGraph 吃力 |
| 极致并发性能、资源精细隔离 | **SEDA** | stage + channel 为高并发而生 |
| 非开发者要可视化改流程 | **SEDA** | JSON 配置驱动，利于编排平台 |
| 已有大量 SEDA 算子资产 | **SEDA** | 复用现成算子，无需重写 |

---

## 五、给你的建议

1. **不是二选一**：LangGraph 适合快速起步和标准 Agent；你的数字人这类"实时抢占 + 极致并发"的生产系统，SEDA 仍是更合适的底座。
2. **借 LangGraph 的思想优化 SEDA 认知**：reducer、Checkpointer、interrupt 这些抽象，能帮你更清晰地审视自己框架里对应的手工实现。
3. **判断力 > 工具**：你现在既懂 prebuilt 的省事，也懂手搓的必要，能顺着"耦合"切模块边界——这套判断力，比记住任何一个 API 都值钱。

