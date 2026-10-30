"""
第 10 讲：create_react_agent —— 第 9 讲那套循环，一行封装

第 9 讲你手搓了 agent⇄tools 循环（StateGraph + agent 节点 + ToolNode + tools_condition + 边）。
生产里这种"标准 Agent"其实一行就能建出来 —— create_react_agent 帮你把那张图封装好了。

ReAct = Reasoning + Acting：模型"推理一步、行动（调工具）一步"交替进行，直到给出答案。
内部结构就是你第 9 讲画的那张图，一模一样。

运行前：确保 .env 里配好 DEEPSEEK_API_KEY。
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

load_dotenv()


@tool
def get_weather(city: str) -> str:
    """查询某个城市的实时天气。参数 city 是中文城市名。"""
    fake = {"北京": "晴，15℃", "上海": "多云，20℃"}
    return fake.get(city, f"{city}：暂无数据")


@tool
def add(a: int, b: int) -> int:
    """计算两个整数相加的结果。"""
    return a + b


llm = ChatOpenAI(model="deepseek-chat", base_url="https://api.deepseek.com",
                 api_key=os.environ["DEEPSEEK_API_KEY"])

# ⭐ 一行搞定：等价于第 9 讲手搓的整张 agent⇄tools 图
# 注意：LangGraph V1.0 起 create_react_agent 已迁移并改名为 create_agent
# （从 langchain.agents 导入，系统提示词参数由 prompt 改为 system_prompt）
agent = create_agent(
    llm,
    tools=[get_weather, add],
    system_prompt="你是一个简洁的助手，回答控制在两句话以内。",   # 系统提示词
)


if __name__ == "__main__":
    for q in ["北京天气怎么样？", "帮我算 123 加 456 等于多少", "你好呀"]:
        print(f"\n{'='*45}\n问：{q}\n{'='*45}")
        result = agent.invoke({"messages": [HumanMessage(content=q)]})
        print("答：", result["messages"][-1].content)
