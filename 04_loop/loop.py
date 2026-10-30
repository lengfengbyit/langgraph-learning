"""
第 5 讲：循环 loop —— 让图"绕回去重做"

LangGraph 没有专门的循环语法：循环 = 用条件边把箭头指回走过的节点。
场景：计数器反复 +1，检查"到 3 没"，没到就回炉重跑，到了才结束。

对照你的 SEDA 成环边：
  LangGraph recursion_limit（当前版本默认 10007，老版本是 25）  ≈  你的 circleRunCountLimit
  都是"支持循环，但必须有'跑多少次就强制刹车'的保险"

补充：recursion_limit 是整次 run 的全局预算，表达不了"这个环最多转 3 圈"，
见 loop_guard.py —— 计数器 / RemainingSteps / recursion_limit 三种刹车的对比。
"""

import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError


class State(TypedDict):
    count: int
    log: Annotated[list[str], operator.add]   # 复习第3讲：追加语义，累积每轮记录


def increment(state: State) -> dict:
    new = state["count"] + 1
    print(f"  [increment] {state['count']} → {new}")
    return {"count": new, "log": [f"第{new}次"]}


def check(state: State) -> str:
    """路由函数：到 3 收工，否则回炉"""
    return "done" if state["count"] >= 3 else "continue"


builder = StateGraph(State)
builder.add_node("increment", increment)
builder.add_edge(START, "increment")
builder.add_conditional_edges("increment", check, {
    "continue": "increment",   # ← 指回自己，这就形成了环！
    "done": END,
})
graph = builder.compile()


if __name__ == "__main__":
    print("【正常循环】到 3 就停：")
    result = graph.invoke({"count": 0, "log": []})
    print("结束，count =", result["count"], " log =", result["log"])

    print("\n【触发刹车】把 recursion_limit 设成 2，来不及到 3：")
    try:
        graph.invoke({"count": 0, "log": []}, config={"recursion_limit": 2})
    except GraphRecursionError:
        print("  ❌ 撞上 recursion_limit，被强制刹车（对照你的 circleRunCountLimit 超限跳出）")
