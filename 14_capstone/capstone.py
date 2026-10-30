"""
第 15 讲：实战篇 —— 用 LangGraph 搭一个简化版数字人对话流

把前 14 讲串成一个能跑的系统。架构：
  START → classify(意图判断)
            ├─(闲聊)────────→ chitchat ───────────────────→ END
            └─(查资料)─→ [web_search ∥ rag] → aggregate → tool_reply → END

用到：条件边(4) + 并行(6) + reducer(3) + 调模型(8) + 节点/边/状态(1-2)

说明：工具(web_search/rag)用模拟数据；意图判断用规则(真实场景可换 LLM)；
     最终回复用真 DeepSeek 生成。刻意不做"抢占取消"(见第14讲讨论，那是 LangGraph 短板)。

运行前：确保 .env 里配好 DEEPSEEK_API_KEY。
"""

import os
import operator
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

load_dotenv()
llm = ChatOpenAI(model="deepseek-chat", base_url="https://api.deepseek.com",
                 api_key=os.environ["DEEPSEEK_API_KEY"])


class State(TypedDict):
    query: str
    intent: str
    tool_results: Annotated[list[str], operator.add]   # 并行工具写入，reducer 合并
    answer: str


def classify(state: State) -> dict:
    q = state["query"]
    intent = "search" if any(k in q for k in ["天气", "比赛", "查", "最新", "新闻"]) else "chitchat"
    print(f"  [classify] 意图 = {intent}")
    return {"intent": intent}


def route(state: State):
    # 查资料：返回列表 = 同一超步并行触发 web_search 和 rag 两个节点
    if state["intent"] == "search":
        return ["web_search", "rag"]
    return "chitchat"


def chitchat(state: State) -> dict:
    resp = llm.invoke([SystemMessage(content="你是亲切的数字人，两句话内闲聊回应。"),
                       HumanMessage(content=state["query"])])
    return {"answer": resp.content}


def web_search(state: State) -> dict:
    print("  [web_search] 并行查询中...")
    return {"tool_results": [f"[网络搜索] 关于「{state['query']}」的网页结果"]}


def rag(state: State) -> dict:
    print("  [rag] 并行检索知识库中...")
    return {"tool_results": [f"[知识库] 关于「{state['query']}」的内部资料"]}


def aggregate(state: State) -> dict:
    print(f"  [aggregate] 汇聚 {len(state['tool_results'])} 条工具结果")
    return {}


def tool_reply(state: State) -> dict:
    context = "\n".join(state["tool_results"])
    resp = llm.invoke([SystemMessage(content=f"你是数字人。依据以下资料两句话内回答用户：\n{context}"),
                       HumanMessage(content=state["query"])])
    return {"answer": resp.content}


builder = StateGraph(State)
for name, fn in [("classify", classify), ("chitchat", chitchat), ("web_search", web_search),
                 ("rag", rag), ("aggregate", aggregate), ("tool_reply", tool_reply)]:
    builder.add_node(name, fn)

builder.add_edge(START, "classify")
# 条件边：闲聊→chitchat；查资料→并行触发 web_search + rag（route 返回列表）
builder.add_conditional_edges("classify", route, ["chitchat", "web_search", "rag"])
builder.add_edge("web_search", "aggregate")
builder.add_edge("rag", "aggregate")
builder.add_edge("aggregate", "tool_reply")
builder.add_edge("chitchat", END)
builder.add_edge("tool_reply", END)
graph = builder.compile()


if __name__ == "__main__":
    for q in ["今天北京天气怎么样", "你好呀，最近开心吗"]:
        print(f"\n{'='*45}\n问：{q}")
        r = graph.invoke({"query": q, "intent": "", "tool_results": [], "answer": ""})
        print("答：", r["answer"])
