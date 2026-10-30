"""
第 11 讲：持久化记忆（Checkpointer）—— 让 Agent 记住多轮对话

痛点：前面每次 graph.invoke() 都是"失忆"的，图不记得上一轮说过什么。
真实对话必须有记忆。Checkpointer 就是干这个的：自动保存每一步的 state，
下次用同一个 thread_id 调用时，自动把历史加载回来。

关键两件事：
  1. 编译时挂上 checkpointer：compile(checkpointer=...)
  2. 调用时带 thread_id：区分不同会话，同一 thread_id 共享记忆

对照你的 SEDA：thread_id ≈ 你的会话/session id；
            Checkpointer ≈ op_context_manager + FlowContext 里跨轮维护的对话历史。

运行前：确保 .env 里配好 DEEPSEEK_API_KEY。
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

llm = ChatOpenAI(model="deepseek-chat", base_url="https://api.deepseek.com",
                 api_key=os.environ["DEEPSEEK_API_KEY"])


def chatbot(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)

# ⭐ 关键：编译时挂上 checkpointer（这里用内存版 MemorySaver，程序退出即丢）
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)


if __name__ == "__main__":
    # thread_id 标识一个会话；同一 thread_id 的多次 invoke 共享记忆
    cfg = {"configurable": {"thread_id": "user-xiaoming"}}

    print("第1轮：告诉它我的名字")
    r1 = graph.invoke({"messages": [HumanMessage(content="你好，我叫小明")]}, cfg)
    print("答：", r1["messages"][-1].content)

    print("\n第2轮：直接问它（不再重复名字），看它记不记得")
    r2 = graph.invoke({"messages": [HumanMessage(content="我叫什么名字？")]}, cfg)
    print("答：", r2["messages"][-1].content)

    print("\n【对比】换一个新 thread_id = 新会话，没有记忆")
    cfg2 = {"configurable": {"thread_id": "someone-else"}}
    r3 = graph.invoke({"messages": [HumanMessage(content="我叫什么名字？")]}, cfg2)
    print("答：", r3["messages"][-1].content)
