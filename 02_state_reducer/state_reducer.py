"""
第 3 讲：State 深入 —— 状态是"覆盖"还是"追加"？

核心问题：节点返回 {"key": value} 时，value 是替换掉旧值，还是和旧值合并？
答案取决于你给这个字段配没配 "reducer（合并函数）"。
  - 不配 reducer（默认）：覆盖，last-write-wins（后写的赢）
  - 配了 reducer：按 reducer 规则合并（list 追加、数字相加……）

对照你的 SEDA FlowContext：
  普通 Set(key, v)        → 覆盖（= 默认语义）
  flowcontext.Push(key,v) → 往 slice 追加（= 配了"追加"reducer 的效果）
"""

import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    # 字段1：默认语义（无 reducer）→ 每次节点返回都会"覆盖"它
    last_step: str
    # 字段2：用 Annotated 绑定 reducer=operator.add → 对 list 就是"追加/拼接"
    history: Annotated[list[str], operator.add]


def step_a(state: State) -> dict:
    return {"last_step": "step_a", "history": ["step_a 到此一游"]}


def step_b(state: State) -> dict:
    return {"last_step": "step_b", "history": ["step_b 到此一游"]}


builder = StateGraph(State)
builder.add_node("a", step_a)
builder.add_node("b", step_b)
builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("b", END)
graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke({"last_step": "", "history": []})
    print("last_step（覆盖语义）:", result["last_step"])
    print("history （追加语义）:", result["history"])
    print("\n看出区别了吗？")
    print("  last_step 只剩最后一个节点写的值  → 被覆盖了")
    print("  history  两个节点写的都在         → 被追加累积了")
