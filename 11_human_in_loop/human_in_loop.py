"""
第 12 讲：人机协作 Human-in-the-loop —— 让图"暂停、等人工、再继续"

场景：Agent 要执行敏感操作（转账/删库/发邮件）前，暂停下来等人工审批。
核心：节点里调 interrupt(payload) → 图立刻暂停，把 payload 抛给人；
     人工决定后，用 Command(resume=决定) 再次 invoke → 从暂停处恢复。

依赖第 11 讲的 Checkpointer：能存档，才能暂停后恢复。所以必须 compile(checkpointer=...)。

对照你的 SEDA：正好对上你项目的 library/interrupt + 干预(intervention)机制。

本讲用纯逻辑演示（不调模型），可直接跑、不耗额度。
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command


class State(TypedDict):
    action: str
    result: str


def prepare(state: State) -> dict:
    """准备一个敏感操作"""
    return {"action": "给 1348207308@qq.com 转账 1000 元"}


def human_approval(state: State) -> dict:
    """关键节点：暂停，把操作详情抛给人审批"""
    decision = interrupt({                       # ⏸ 执行到这里，整张图暂停
        "question": "是否批准以下操作？",
        "action": state["action"],
    })
    # 人工 resume 之后，interrupt() 才返回人给的值，继续往下走
    return {"result": "approve" if decision == "approve" else "reject"}


def execute(state: State) -> dict:
    """根据人工决定执行或拒绝"""
    if state["result"] == "approve":
        return {"result": f"✅ 已执行：{state['action']}"}
    return {"result": f"❌ 已拒绝：{state['action']}"}


builder = StateGraph(State)
builder.add_node("prepare", prepare)
builder.add_node("human_approval", human_approval)
builder.add_node("execute", execute)
builder.add_edge(START, "prepare")
builder.add_edge("prepare", "human_approval")
builder.add_edge("human_approval", "execute")
builder.add_edge("execute", END)

graph = builder.compile(checkpointer=MemorySaver())   # 必须有 checkpointer 才能暂停/恢复


if __name__ == "__main__":
    cfg = {"configurable": {"thread_id": "approval-1"}}

    # 第一次 invoke：跑到 interrupt 处暂停
    r1 = graph.invoke({"action": "", "result": ""}, cfg)
    intr = r1["__interrupt__"][0].value            # 取出暂停时抛给人的 payload
    print("⏸ 图暂停，等待人工审批：")
    print("   操作:", intr["action"])

    decision = input("   输入 approve 批准 / reject 拒绝：").strip()

    # 第二次 invoke：用 Command(resume=...) 从暂停处恢复
    r2 = graph.invoke(Command(resume=decision), cfg)
    print("▶ 恢复执行，最终结果:", r2["result"])
