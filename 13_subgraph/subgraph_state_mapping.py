"""
第 14 讲补充：父子图 state 字段不一致时，状态怎么流转

subgraph.py 里父子字段同名（都有 text），所以"塞进去就能跑"。
真实项目里父子 schema 往往不同，先记住三条事实（本文件逐个验证）：

  1. 直接把子图当节点 = 按【同名 key】隐式映射：
     父图只把"和子图同名的字段"传进子图，父子各自独有的字段互相看不见。
  2. 子图返回的、父图 schema 里没有的 key 会被【静默丢弃】，不报错。
     字段对不上时数据是"悄悄没了"，不是报错——最难查的那种 bug。
  3. 字段语义/名字不同时，用一个【包装函数】显式做入参和出参映射（推荐）。

对照 SEDA：相当于子流程的入参/出参映射（inputMap / outputMap），
而不是靠变量同名硬碰。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# ══════════════════════════════════════════════════════════════
# 子图：检索流程。字段叫 query / findings / sources
# ══════════════════════════════════════════════════════════════
class ResearchState(TypedDict):
    query: str
    findings: str
    sources: list[str]


def search_node(s: ResearchState) -> dict:
    print(f"    [子图] 收到的 state = {s}")
    return {
        "findings": f"关于「{s['query']}」的结论",
        "sources": ["doc-1", "doc-2"],
    }


sub_builder = StateGraph(ResearchState)
sub_builder.add_node("search", search_node)
sub_builder.add_edge(START, "search")
sub_builder.add_edge("search", END)
research_graph = sub_builder.compile()


# ── A1：父子有部分同名字段（query）──────────────────────────
class ParentA(TypedDict):
    query: str        # 和子图同名 → 会传进去
    user_id: str      # 子图看不到
    answer: str       # 子图没有这个字段


def embed(subgraph) -> object:
    """把子图直接当成一个节点，不做任何字段映射"""
    b = StateGraph(ParentA)
    b.add_node("research", subgraph)
    b.add_edge(START, "research")
    b.add_edge("research", END)
    return b.compile()


# ── A2：完全对不上（父叫 user_query）────────────────────────
class ParentB(TypedDict):
    user_query: str   # 和子图的 query 不同名
    user_id: str
    answer: str


# ══════════════════════════════════════════════════════════════
# B. 正解：包装函数显式映射入参 / 出参
# ══════════════════════════════════════════════════════════════
class ParentC(TypedDict):
    user_query: str
    user_id: str
    answer: str
    trace: list[str]


def call_research(s: ParentC) -> dict:
    """入参映射：父 user_query → 子 query
       出参映射：子 findings → 父 answer，并补上父图特有的审计信息"""
    out = research_graph.invoke({"query": s["user_query"]})
    return {
        "answer": out["findings"],
        "trace": [f"用户 {s['user_id']} 检索完成，来源 {len(out['sources'])} 条"],
    }


def wrap() -> object:
    b = StateGraph(ParentC)
    b.add_node("research", call_research)
    b.add_edge(START, "research")
    b.add_edge("research", END)
    return b.compile()


if __name__ == "__main__":
    print("【A1. 部分同名：query 能进去，findings 出不来】")
    r = embed(research_graph).invoke({"query": "LangGraph 怎么做循环", "user_id": "u1", "answer": ""})
    print("  父图结果:", r)
    print("  → query 传进去了；子图的 findings/sources 被静默丢弃，answer 仍是空；user_id 子图也没看到\n")

    print("【A2. 完全对不上：子图拿到空 state】")
    b_builder = StateGraph(ParentB)
    b_builder.add_node("research", research_graph)
    b_builder.add_edge(START, "research")
    b_builder.add_edge("research", END)
    try:
        b_builder.compile().invoke({"user_query": "LangGraph 怎么做循环", "user_id": "u1", "answer": ""})
    except KeyError as e:
        print(f"  → 子图读 s['query'] 直接 KeyError: {e}（这次至少是显式报错）\n")

    print("【B. 包装函数做映射】")
    r = wrap().invoke({"user_query": "LangGraph 怎么做循环", "user_id": "u1", "answer": "", "trace": []})
    print("  父图结果:", r)
