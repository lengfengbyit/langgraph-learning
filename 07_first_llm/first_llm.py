"""
第 8 讲：第一次在节点里调用大模型 —— 从"函数节点"到"智能节点"

前 7 讲的节点都是写死逻辑的普通函数。这一讲，节点内部第一次真正调用 LLM。
用 DeepSeek（兼容 OpenAI 接口，所以用 ChatOpenAI 改 base_url 即可）。

运行前准备（自己做）：
  1. uv add langchain-openai python-dotenv
  2. 复制 .env.example 为 .env，填入你的 DEEPSEEK_API_KEY
  3. .venv/bin/python 07_first_llm/first_llm.py
"""

import os
from typing import TypedDict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

load_dotenv()   # 从同目录/项目根的 .env 读取环境变量（把 API Key 加载进来）


class State(TypedDict):
    question: str
    answer: str


# 创建指向 DeepSeek 的 LLM 客户端（全局建一次即可，不必每次调用都 new）
# DeepSeek 兼容 OpenAI 协议：沿用 ChatOpenAI，只需把 base_url 改成 DeepSeek 的地址
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.environ["DEEPSEEK_API_KEY"],   # 缺失会直接 KeyError，提醒你没配 key
    temperature=0.7,
)


def chatbot(state: State) -> dict:
    """智能节点：把问题丢给 LLM，拿回答案"""
    messages = [
        # SystemMessage：设定角色/规则（相当于给模型的"系统提示词"）
        SystemMessage(content="你是一个简洁幽默的助手，回答控制在两句话以内。"),
        # HumanMessage：用户这轮说的话
        HumanMessage(content=state["question"]),
    ]
    resp = llm.invoke(messages)        # 调模型，返回一条 AIMessage
    return {"answer": resp.content}    # .content 是回复的纯文本


builder = StateGraph(State)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)
graph = builder.compile()


if __name__ == "__main__":
    q = "用一句话解释什么是递归"
    result = graph.invoke({"question": q, "answer": ""})
    print("问:", q)
    print("答:", result["answer"])
