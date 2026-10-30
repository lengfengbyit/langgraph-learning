"""
第 14 讲补充 2：包装函数里调子图，子图内的 interrupt 还能不能续上？

结论（本文件可验证）：能。
父图重跑包装函数时，子图并不会从 START 重跑，而是从【自己被中断的那个节点】继续。
原因是两件事由 config 自动透传：

  1. checkpointer 透传（pregel/main.py:857）：子图没传 checkpointer 时，
     会拿父图 config 里的 CONFIG_KEY_CHECKPOINTER，于是子图也在同一份 saver 里落盘，
     只是换了命名空间 sub:<task_id>。
  2. 恢复标记透传（pregel/_loop.py:1188）：父图处于 resume 状态时，
     子图的 input 会被忽略，直接从自己的 pending 节点续跑。

代价：包装函数【本身】会整个重跑（引用计数、日志、它自己的外部副作用都会再来一次），
所以包装函数里 interrupt 之外的副作用同样要幂等。
"""

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

RUNS = {"prepare": 0, "approve": 0, "finish": 0}   # 统计每个节点实际执行次数


class State(TypedDict):
    query: str
    steps: Annotated[list[str], operator.add]


def prepare(s: State) -> dict:
    RUNS["prepare"] += 1
    return {"steps": [f"prepare({s['query']})"]}


def approve(s: State) -> dict:
    RUNS["approve"] += 1
    ok = interrupt({"question": "子图内审批：是否继续？", "query": s["query"]})
    return {"steps": [f"approve={'✓' if ok == 'approve' else '✗'}"]}


def finish(s: State) -> dict:
    RUNS["finish"] += 1
    return {"steps": ["finish"]}


# ── 子图：故意不传 checkpointer ──────────────────────────────
sub_builder = StateGraph(State)
sub_builder.add_node("prepare", prepare)
sub_builder.add_node("approve", approve)
sub_builder.add_node("finish", finish)
sub_builder.add_edge(START, "prepare")
sub_builder.add_edge("prepare", "approve")
sub_builder.add_edge("approve", "finish")
sub_builder.add_edge("finish", END)
subgraph = sub_builder.compile()


# ── 父图：用包装函数调子图（字段映射顺便做一次）──────────────
def call_subgraph(s: State) -> dict:
    print("  [wrapper] 执行（每次 resume 都会重新进这里）")
    out = subgraph.invoke({"query": s["query"]})
    return {"query": out["query"], "steps": out["steps"]}


parent_builder = StateGraph(State)
parent_builder.add_node("research", call_subgraph)
parent_builder.add_edge(START, "research")
parent_builder.add_edge("research", END)
graph = parent_builder.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "wrap-interrupt"}}

    r = graph.invoke({"query": "退款流程", "steps": []}, cfg)
    print("⏸ 父图收到中断:", r["__interrupt__"][0].value)
    print("  节点执行次数:", RUNS)

    r = graph.invoke(Command(resume="approve"), cfg)
    print("▶ 恢复后最终 state:", r)
    print("  节点执行次数:", RUNS)
    print("  → prepare 只跑了 1 次：子图是从自己被中断的 approve 续跑的，没回到 START")

    print("\ncheckpoint 命名空间:", list(graph.checkpointer.storage["wrap-interrupt"].keys()))
    print("  → 子图没有自己的 saver，但借父图的 saver 落在了 'research:<task_id>' 命名空间下")
