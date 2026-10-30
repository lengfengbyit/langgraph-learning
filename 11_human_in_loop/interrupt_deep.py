"""
第 12 讲补充：interrupt 的两个深坑 —— 节点会重跑、多个 interrupt 怎么匹配

human_in_loop.py 只演示了一次暂停 + 一次恢复。真到业务里会遇到：

  坑 1：一个节点里有多个 interrupt()，每次 resume 都会从节点开头重跑，
        逐个"吃掉"答案，直到所有 interrupt 都拿到值才算跑完。
  坑 2：重跑意味着 interrupt() 之前的副作用（扣款、发消息）会执行多次。

本文件用两个独立的图把这两件事跑出来，不调模型、不需要人工输入。
对照 SEDA：恢复粒度是"节点整段重放"，不是"算子内部某一行续跑"，
所以幂等性得自己做。
"""

import operator
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


# =====================================================================
# 场景 1：一个节点里两个 interrupt，答案按"调用序号"逐个匹配
# =====================================================================
class TransferState(TypedDict):
    result: str


def transfer(state: TransferState) -> dict:
    print("    [transfer] 节点从头开始执行")
    amount = interrupt("确认转账金额？")     # 序号 0
    print(f"    [transfer] 拿到第 1 个答案: {amount}")
    channel = interrupt("确认到账渠道？")    # 序号 1
    print(f"    [transfer] 拿到第 2 个答案: {channel}")
    return {"result": f"{channel} 转账 {amount} 元"}


b1 = StateGraph(TransferState)
b1.add_node("transfer", transfer)
b1.add_edge(START, "transfer")
b1.add_edge("transfer", END)
two_step_graph = b1.compile(checkpointer=MemorySaver())


# =====================================================================
# 场景 2：副作用写在 interrupt() 之前 → 恢复时被执行两次
# =====================================================================
class OrderState(TypedDict):
    order: str
    result: str


PAYMENTS: list[str] = []   # 模拟外部支付系统（不会随图回滚）


def bad_node(state: OrderState) -> dict:
    PAYMENTS.append(f"扣款 {state['order']}")      # ❌ 在 interrupt 之前就扣了
    ok = interrupt(f"是否放行订单 {state['order']}？")
    return {"result": "已放行" if ok == "approve" else "已取消"}


def good_node(state: OrderState) -> dict:
    ok = interrupt(f"是否放行订单 {state['order']}？")
    PAYMENTS.append(f"扣款 {state['order']}")      # ✅ 人工批准后才扣
    return {"result": "已放行" if ok == "approve" else "已取消"}


def build_payment_graph(node) -> object:
    b = StateGraph(OrderState)
    b.add_node("pay", node)
    b.add_edge(START, "pay")
    b.add_edge("pay", END)
    return b.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    # ---------- 场景 1 ----------
    cfg = {"configurable": {"thread_id": "two-step"}}
    print("【场景 1】两个 interrupt，恢复两次")

    r = two_step_graph.invoke({"result": ""}, cfg)
    print("  ⏸ 第 1 次暂停:", r["__interrupt__"][0].value)

    r = two_step_graph.invoke(Command(resume="1000"), cfg)
    print("  ⏸ 第 2 次暂停:", r["__interrupt__"][0].value, "（节点又重跑了一遍）")

    r = two_step_graph.invoke(Command(resume="支付宝"), cfg)
    print("  ▶ 完成:", r["result"], "\n")

    # ---------- 场景 2 ----------
    print("【场景 2】副作用放在 interrupt() 之前的后果")

    PAYMENTS.clear()
    bad = build_payment_graph(bad_node)
    bad.invoke({"order": "A001", "result": ""}, {"configurable": {"thread_id": "bad"}})
    bad.invoke(Command(resume="approve"), {"configurable": {"thread_id": "bad"}})
    print(f"  ❌ 错位写法：支付系统里共 {len(PAYMENTS)} 笔 = {PAYMENTS} → 重复扣款")

    PAYMENTS.clear()
    good = build_payment_graph(good_node)
    good.invoke({"order": "A002", "result": ""}, {"configurable": {"thread_id": "good"}})
    good.invoke(Command(resume="approve"), {"configurable": {"thread_id": "good"}})
    print(f"  ✅ 正确写法：支付系统里共 {len(PAYMENTS)} 笔 = {PAYMENTS}")
