"""
第 13 讲：流式输出（Streaming）—— 让回答像打字机一样一个字一个字吐

前面都用 graph.invoke()：等整张图跑完，一次性拿到结果。
但真实对话里，用户希望"边生成边看到"（打字机效果），而不是干等几秒后一下蹦出一大段。
graph.stream() 就是干这个的：边算边 yield。

三种常用 stream_mode：
  - "updates"：每个节点跑完 yield 一次它的增量更新（看流程推进）
  - "values" ：每步后 yield 一次完整 state
  - "messages"：LLM 的 token 级流式，逐字吐（最像打字机，最贴近你的 SSE）

对照你的 SEDA：stream_mode="messages" ≈ 你的 LLM 流式 + streamproc 逐句处理 + SSE 推送。

运行前：确保 .env 里配好 DEEPSEEK_API_KEY。
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState

load_dotenv()

llm = ChatOpenAI(model="deepseek-chat", base_url="https://api.deepseek.com",
                 api_key=os.environ["DEEPSEEK_API_KEY"])


def chatbot(state: MessagesState) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


builder = StateGraph(MessagesState)
builder.add_node("chatbot", chatbot)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)
graph = builder.compile()


if __name__ == "__main__":
    q = "用三句话介绍一下杭州"
    print("问:", q)
    print("答: ", end="", flush=True)
    # token: content='' additional_kwargs={} response_metadata={'model_provider': 'openai'} id='lc_run--01a18c00-191f-7631-b8d1-7dee1c06a592' tool_calls=[] invalid_tool_calls=[] tool_call_chunks=[]
    # metadata: {'ls_integration': 'langchain_chat_model', 'langgraph_step': 1, 'langgraph_node': 'chatbot', 'langgraph_triggers': ('branch:to:chatbot',), 'langgraph_path': ('__pregel_pull', 'chatbot'), 'langgraph_checkpoint_ns': 'chatbot:3a7cac91-ae04-9fac-1b56-3bbec5913ef4', 'checkpoint_ns': 'chatbot:3a7cac91-ae04-9fac-1b56-3bbec5913ef4', 'ls_provider': 'openai', 'ls_model_name': 'deepseek-chat', 'ls_model_type': 'chat', 'ls_temperature': None, 'lc_versions': {'langchain-core': '1.7.3', 'langchain': '1.4.7', 'langchain-openai': '1.7.3'}}

    # stream_mode="messages"：逐 token 流式，返回 (token块, 元数据) 二元组
    for token, metadata in graph.stream(
        {"messages": [HumanMessage(content=q)]},
        stream_mode="messages",
    ):
        print(token.content, end="", flush=True)   # 一个字一个字打印出来
    print()
