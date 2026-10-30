"""
第 5 讲补充：循环的三种"刹车" —— 为什么 recursion_limit 不够用

loop.py 只演示了最粗暴的那种：recursion_limit 撞墙 → GraphRecursionError 中断整个 run。
但 recursion_limit 是**整次 run 的全局 superstep 预算**，表达不了
"这个环最多转 3 圈"这种局部语义。按离业务由近到远，有三档：

  1. state 计数器 + 条件边   最精确：环自己数圈，数到就走 END，正常结束
  2. RemainingSteps         半自动：读到全局还剩几步，快用完时主动收尾（不抛异常）
  3. recursion_limit        总闸：兜底防跑飞，触发即中断并抛异常

调用方每次 invoke 都能改 recursion_limit，所以它是"这一跑的总预算"，
不是图的固有属性，更不是某条边的属性（add_edge 没有次数参数）。
"""

import operator
from typing import Annotated, TypedDict

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.managed.is_last_step import RemainingSteps

MAX_LOOPS = 3   # 业务语义：这个环最多转 3 圈


class State(TypedDict):
    count: int
    log: Annotated[list[str], operator.add]
    remaining: RemainingSteps   # 框架注入：距 recursion_limit 还剩几步


def increment(state: State) -> dict:
    new = state["count"] + 1
    print(f"  [increment] 第 {new} 次, remaining={state['remaining']}")
    return {"count": new, "log": [f"第{new}次"]}


# ---------- 1. 计数器兜底：环自己决定何时停 ----------
def route_by_counter(state: State) -> str:
    return "done" if state["count"] >= MAX_LOOPS else "again"


b1 = StateGraph(State)
b1.add_node("increment", increment)
b1.add_edge(START, "increment")
b1.add_conditional_edges("increment", route_by_counter, {"again": "increment", "done": END})
counter_graph = b1.compile()


# ---------- 2. RemainingSteps 兜底：快撞总闸前主动收尾 ----------
def route_by_remaining(state: State) -> str:
    return "done" if state["remaining"] <= 2 else "again"


b2 = StateGraph(State)
b2.add_node("increment", increment)
b2.add_edge(START, "increment")
b2.add_conditional_edges("increment", route_by_remaining, {"again": "increment", "done": END})
remaining_graph = b2.compile()


# ---------- 3. 不设业务兜底：只能靠 recursion_limit 硬刹 ----------
b3 = StateGraph(State)
b3.add_node("increment", increment)
b3.add_edge(START, "increment")
b3.add_edge("increment", "increment")   # 纯自环，没有任何出口
raw_loop = b3.compile()


if __name__ == "__main__":
    print(f"【1. 计数器兜底】环自己数到 {MAX_LOOPS} 就停，recursion_limit 给多大都不影响：")
    r = counter_graph.invoke({"count": 0, "log": []}, config={"recursion_limit": 100})
    print(f"  ✅ 正常结束 count={r['count']} log={r['log']}\n")

    print("【2. RemainingSteps 兜底】剩 2 步时主动收尾，不抛异常：")
    r = remaining_graph.invoke({"count": 0, "log": []}, config={"recursion_limit": 10})
    print(f"  ✅ 正常结束 count={r['count']}，共转 {r['count']} 圈，没撞墙\n")

    print("【3. 只有 recursion_limit】limit=4，转满 4 圈被强制中断：")
    try:
        raw_loop.invoke({"count": 0, "log": []}, config={"recursion_limit": 4})
    except GraphRecursionError:
        print("  ❌ 撞上 recursion_limit → GraphRecursionError（整个 run 中断）")
