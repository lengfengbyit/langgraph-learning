"""
第 2 讲：你的第一个 LangGraph 图（最简版，不调用大模型）

目标：用「两个节点 + 一条边」拼出一句话 "你好，世界！"
对照你项目里的 conf/flow/hello_world_graph.conf —— 同样是 2 节点 1 边，
区别是：那边用 JSON 配置搭图，这边用 Python 代码搭图。
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


# ── 1. 定义「状态 State」──────────────────────────────
# State 就是第 1 讲说的"全程流动的共享笔记本"。
# 这里用 TypedDict 声明：笔记本里只有一个字段 message（字符串）。
# 对照你的 SEDA：这相当于 FlowContext 这块"全局黑板"，只是这里用类型声明得很明确。
class State(TypedDict):
    message: str


# ── 2. 定义「节点 Node」──────────────────────────────
# LangGraph 的节点就是一个普通函数：输入当前 state，返回"要更新进 state 的字段"。
# 对照你的 SEDA：这相当于一个 Operator 的 DoImpl()，但轻量得多（不用嵌 struct、不用三段式）。

def hello_node(state: State) -> dict:
    """第一个节点：往笔记本写入 '你好'"""
    print("  [hello_node] 正在执行，写入 '你好'")
    return {"message": "你好"}


def world_node(state: State) -> dict:
    """第二个节点：读出笔记本已有内容，追加 '，世界！'"""
    print(f"  [world_node] 读到上游写的内容: '{state['message']}'")
    return {"message": state["message"] + "，世界！"}


# ── 3. 搭图：把节点和边组装起来 ──────────────────────
builder = StateGraph(State)        # 新建一张图，并告诉它状态长什么样
builder.add_node("hello", hello_node)   # 注册节点，起名 "hello"
builder.add_node("world", world_node)   # 注册节点，起名 "world"

builder.add_edge(START, "hello")   # 边：图的入口 → hello（START 是内置的起点）
builder.add_edge("hello", "world") # 边：hello → world
builder.add_edge("world", END)     # 边：world → 出口（END 是内置的终点）

graph = builder.compile()          # 编译成可执行的图


# ── 4. 运行 ────────────────────────────────────────
if __name__ == "__main__":
    print("开始执行图：")
    # invoke 传入初始 state；这里从空字符串起步
    result = graph.invoke({"message": ""})
    print("\n最终状态:", result)
    print("最终消息:", result["message"])
