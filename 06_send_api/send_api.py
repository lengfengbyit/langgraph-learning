"""
第 7 讲：Send API —— 运行时动态并行（map-reduce）

第 6 讲的 fan-out 是"静态"的：编译时就写死三条边（web/rag/live）。
但真实场景常常运行时才知道要并行几路 —— 比如把一个复杂任务拆成 N 个子任务，
N 不固定。这就是 Send：动态扇出，有几个就派几个。

对照你的数字人 op_task_split：把一个 query 拆成若干子任务并行处理，数量不定。

实战提醒：这是一个真实的坑。如果你指望 summarize 做收尾（比如写数据库、返回兜底响应），一旦动态派发恰好是 0 路，收尾逻辑就被整个跳过了。稳妥做法是：要么保证至少派一路，要么用一条从 START 直达 summarize 的旁路边兜底。你 SEDA 里 op_output/op_end 必执行的设计，就是在防这类"收尾被跳过"。
"""

import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class State(TypedDict):
    topics: list[str]                            # 运行时输入，数量不定
    jokes: Annotated[list[str], operator.add]    # 并行结果汇总（reducer 合并）


class JokeState(TypedDict):
    topic: str                                   # 每个并行实例拿到的独立子输入


def dispatch(state: State) -> list[Send]:
    """动态扇出：有几个 topic 就派发几个 gen_joke 实例，各带各的子状态"""
    n = len(state["topics"])
    print(f"  [dispatch] 收到 {n} 个主题，动态派发 {n} 路")
    return [Send("gen_joke", {"topic": t}) for t in state["topics"]]


def gen_joke(state: JokeState) -> dict:
    print(f"    [gen_joke] 处理主题：{state['topic']}")
    return {"jokes": [f"关于「{state['topic']}」的笑话"]}


def summarize(state: State) -> dict:
    print(f"  [summarize] 共收到 {len(state['jokes'])} 条")
    return {}


builder = StateGraph(State)
builder.add_node("gen_joke", gen_joke)
builder.add_node("summarize", summarize)
# 条件边返回 Send 列表 = 动态并行；第三参 ["gen_joke"] 声明可能派到哪些节点
builder.add_conditional_edges(START, dispatch, ["gen_joke"])
builder.add_edge("gen_joke", "summarize")
builder.add_edge("summarize", END)
graph = builder.compile()


if __name__ == "__main__":
    print("【第一次】传 2 个主题：")
    r1 = graph.invoke({"topics": ["猫", "程序员"], "jokes": []})
    print("结果:", r1["jokes"], "\n")

    print("【第二次】传 4 个主题（同一张图，自动并行 4 路）：")
    r2 = graph.invoke({"topics": ["咖啡", "周一", "bug", "加班"], "jokes": []})
    print("结果:", r2["jokes"])
