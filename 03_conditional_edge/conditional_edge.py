"""
第 4 讲：条件边 —— 根据运行结果决定走哪条分支

普通边 add_edge("a","b") 是写死的：跑完 a 必去 b。
条件边 add_conditional_edges 则由一个"路由函数"的返回值动态决定下一步去哪。

本例模拟"意图识别分流"，正好对照你 SEDA 项目里的 op_task_split：
  START → classify(判意图) →（条件边）→ chitchat 或 search → END

对照你的 condition 返回码机制：
  路由函数返回的标签 "search"/"chitchat"  ≈  算子 DoImpl 返回码 ret
  path_map 映射表                          ≈  conf 里边的 condition:1 / condition:2
"""

from typing import TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    query: str    # 用户输入
    intent: str   # 意图识别结果
    answer: str   # 最终回复


def classify(state: State) -> dict:
    """判意图：真实场景这里会调 LLM，现在先用关键词简单模拟"""
    intent = "search" if ("天气" in state["query"] or "查" in state["query"]) else "chitchat"
    print(f"  [classify] query='{state['query']}' → intent='{intent}'")
    return {"intent": intent}


def route(state: State) -> str:
    """路由函数：只读 state、返回一个标签，自己不改 state"""
    return state["intent"]


def chitchat(state: State) -> dict:
    return {"answer": f"（闲聊）随便聊聊「{state['query']}」~"}


def search(state: State) -> dict:
    return {"answer": f"（检索）正在为「{state['query']}」查资料..."}


builder = StateGraph(State)
builder.add_node("classify", classify)
builder.add_node("chitchat", chitchat)
builder.add_node("search", search)

builder.add_edge(START, "classify")
# 条件边：从 classify 出发，用 route 决定去哪；path_map 把"标签"翻译成"节点名"
builder.add_conditional_edges("classify", route, {
    "chitchat": "chitchat",
    "search": "search",
})
builder.add_edge("chitchat", END)
builder.add_edge("search", END)

graph = builder.compile()


if __name__ == "__main__":
    for q in ["今天北京天气怎么样", "哈哈你真有意思"]:
        answer = graph.invoke({"query": q, "intent": "", "answer": ""})["answer"]
        print(f"输入「{q}」→ {answer}\n")
