"""
第 14 讲：子图（Subgraph）—— 把一整张图当成另一张图里的一个节点

当系统变复杂，你会想把它拆成几块、各自独立维护，再组装起来。
LangGraph 的做法：一张编译好的图，可以直接当作另一张图里的【一个节点】。

好处：模块化、可复用、团队分工（不同人负责不同子图），父图只管怎么编排这些块。

state 怎么在父子间传：父图和子图【共享的 key】会自动流转进/出子图。
（本例父子都有 text 字段，所以 text 自动在父子之间传递。schema 不同则需包装函数转换。）

对照你的 SEDA：正好对上你项目的 isSubFlowOp —— 算子内嵌一张完整子图。

本讲用纯逻辑演示（不调模型），可直接跑、不耗额度。
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# ── 子图：一个独立的两步"处理"流程 ──────────────────
class SubState(TypedDict):
    text: str


def sub_step1(s: SubState) -> dict:
    return {"text": s["text"] + " →[子图·步骤1]"}


def sub_step2(s: SubState) -> dict:
    return {"text": s["text"] + " →[子图·步骤2]"}


sub_builder = StateGraph(SubState)
sub_builder.add_node("s1", sub_step1)
sub_builder.add_node("s2", sub_step2)
sub_builder.add_edge(START, "s1")
sub_builder.add_edge("s1", "s2")
sub_builder.add_edge("s2", END)
subgraph = sub_builder.compile()        # 编译成一张独立的图


# ── 父图：把整个子图当成一个节点塞进来 ──────────────
class ParentState(TypedDict):
    text: str


def before(s: ParentState) -> dict:
    return {"text": s["text"] + " →[父图·前置]"}


def after(s: ParentState) -> dict:
    return {"text": s["text"] + " →[父图·后置]"}


parent_builder = StateGraph(ParentState)
parent_builder.add_node("before", before)
parent_builder.add_node("research", subgraph)   # ⭐ 整个子图作为一个节点！
parent_builder.add_node("after", after)
parent_builder.add_edge(START, "before")
parent_builder.add_edge("before", "research")
parent_builder.add_edge("research", "after")
parent_builder.add_edge("after", END)
graph = parent_builder.compile()


if __name__ == "__main__":
    r = graph.invoke({"text": "开始"})
    print("最终 text:", r["text"])
    print("\n看链路：父图前置 → (进子图) 步骤1 → 步骤2 → (出子图) 父图后置")
