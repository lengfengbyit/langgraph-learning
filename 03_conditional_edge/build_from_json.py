"""
用 JSON 描述拓扑 + 通用加载器构造图 —— 对照 conditional_edge.py

分工：
  graph.json   只描述"有哪些节点、谁连谁"（纯数据）
  本文件        提供节点/路由函数，并按 JSON 调 add_node/add_edge（通用代码）

所以不需要"生成代码"：读取 JSON 后直接调 builder 就行。
node 的行为、条件路由的判断逻辑、State 的字段仍必须写在 Python 里，
JSON 里只存它们的"名字"。
"""

import json
from pathlib import Path
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    query: str
    intent: str
    answer: str


def classify(state: State) -> dict:
    intent = "search" if ("天气" in state["query"] or "查" in state["query"]) else "chitchat"
    print(f"  [classify] query='{state['query']}' → intent='{intent}'")
    return {"intent": intent}


def route(state: State) -> str:
    return state["intent"]


def chitchat(state: State) -> dict:
    return {"answer": f"（闲聊）随便聊聊「{state['query']}」~"}


def search(state: State) -> dict:
    return {"answer": f"（检索）正在为「{state['query']}」查资料..."}


# 注册表：JSON 里写名字，这里映射到真正的可调用对象
STATES: dict[str, Any] = {"State": State}
NODE_FUNCS: dict[str, Callable[[State], dict]] = {
    "classify": classify,
    "chitchat": chitchat,
    "search": search,
}
ROUTERS: dict[str, Callable[[State], str]] = {"route": route}


def _endpoint(name: str) -> str:
    """把 JSON 里的 "START"/"END" 字符串换成 langgraph 的常量"""
    return {"START": START, "END": END}.get(name, name)


def build_graph(spec: dict) -> Any:
    """把一份 JSON 拓扑"解释"成编译好的图"""
    builder = StateGraph(STATES[spec["state"]])

    for node in spec["nodes"]:
        builder.add_node(node["name"], NODE_FUNCS[node["fn"]])

    for src, dst in spec["edges"]:
        builder.add_edge(_endpoint(src), _endpoint(dst))

    for ce in spec.get("conditional_edges", []):
        builder.add_conditional_edges(
            _endpoint(ce["from"]),
            ROUTERS[ce["router"]],
            ce.get("path_map"),
        )

    return builder.compile()


if __name__ == "__main__":
    spec = json.loads(Path(__file__).with_name("graph.json").read_text(encoding="utf-8"))
    graph = build_graph(spec)

    for q in ["今天北京天气怎么样", "哈哈你真有意思"]:
        answer = graph.invoke({"query": q, "intent": "", "answer": ""})["answer"]
        print(f"输入「{q}」→ {answer}\n")
