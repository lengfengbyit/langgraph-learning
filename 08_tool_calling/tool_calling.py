"""
第 9 讲：工具调用（Tool Calling）—— Agent 的核心机制

前一讲模型只会"聊天回话"。这一讲让模型学会：面对一个问题，自己判断
"要不要调用外部工具、调哪个、传什么参数"，拿到工具结果后再组织最终回答。

这就是 Agent 的灵魂。本讲手搓一遍 agent⇄tools 循环，第 10 讲再用 prebuilt 一键封装。

对照你的 SEDA：@tool ≈ toolregistry 里注册的 web_search/rag/live_event；
            本讲的 agent⇄tools 循环 ≈ op_task_split 判断调工具 + op_tool_router 汇聚。

运行前：确保已 uv add langchain-openai，且 .env 里配好 DEEPSEEK_API_KEY。
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()


# ── 1. 定义工具 ──────────────────────────────────────
# @tool 把普通函数变成"模型能调的工具"。docstring 至关重要：
# 模型就是靠它（+ 参数名/类型）判断"这个问题该不该用这个工具"。
@tool
def get_weather(city: str) -> str:
    """查询某个城市的实时天气。参数 city 是中文城市名。"""
    fake = {"北京": "晴，15℃", "上海": "多云，20℃"}   # 模拟，真实场景调天气 API
    return fake.get(city, f"{city}：暂无数据")


@tool
def add(a: int, b: int) -> int:
    """计算两个整数相加的结果。"""
    return a + b


tools = [get_weather, add]

# ── 2. 创建 LLM 并"绑定"工具（告诉模型有哪些工具可用）──
llm = ChatOpenAI(model="deepseek-chat", base_url="https://api.deepseek.com",
                 api_key=os.environ["DEEPSEEK_API_KEY"])
llm_with_tools = llm.bind_tools(tools)


# ── 3. agent 节点：调模型。模型可能直接回答，也可能返回"要调工具"的指令 ──
def agent(state: MessagesState) -> dict:
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


# ── 4. 建图：agent ⇄ tools 循环 ──────────────────────
builder = StateGraph(MessagesState)          # MessagesState 内置 messages + add_messages reducer
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))   # 预置节点：自动执行模型要求的 tool_calls
builder.add_edge(START, "agent")
# tools_condition 预置路由：看最后一条 AIMessage 有没有 tool_calls
#   有 → 去 "tools" 执行；没有 → END
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")           # 工具结果回到 agent，让模型据此继续
graph = builder.compile()


if __name__ == "__main__":
    for q in ["北京天气怎么样？", "帮我算 123 加 456 等于多少", "你好啊"]:
        print(f"\n{'='*45}\n问：{q}\n{'='*45}")
        result = graph.invoke({"messages": [HumanMessage(content=q)]})
        for m in result["messages"]:
            m.pretty_print()                 # 打印完整轨迹：Human→AI(tool_calls)→Tool→AI(答案)
