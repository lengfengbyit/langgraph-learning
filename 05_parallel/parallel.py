"""
第 6 讲：并行 fan-out / fan-in —— 一分多、多汇一

fan-out（扇出）：一个节点分叉出多个节点，在同一个"超步(superstep)"里并行跑。
fan-in （扇入）：多个并行节点汇聚到一个节点；LangGraph 会等它们【全部】跑完
                （barrier 栅栏同步）之后，才执行那个汇聚节点。

对照你的数字人场景：并行调 web_search / rag / live_event 三个工具，再汇聚结果。

关键点：三个并行节点都往 results 写，靠第 3 讲的 reducer(operator.add) 安全合并；
       若不给 results 配 reducer，并行写同一个 key 会直接报错 InvalidUpdateError。
"""

import time
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    query: str
    results: Annotated[list[str], operator.add]   # 并行写入 → reducer 负责合并


def dispatch(state: State) -> dict:
    print("  [dispatch] 收到 query，准备并行分发三路")
    return {}


def make_worker(name: str):
    def worker(state: State) -> dict:
        print(f"  [{name}] 开始查询...")
        time.sleep(0.5)                       # 模拟各自耗时 0.5s
        print(f"  [{name}] 查询完成")
        return {"results": [f"{name} 的结果"]}
    return worker


def aggregate(state: State) -> dict:
    print(f"  [aggregate] 三路都到齐了，共收到 {len(state['results'])} 条结果")
    return {}


builder = StateGraph(State)
builder.add_node("dispatch", dispatch)
builder.add_node("web", make_worker("web"))
builder.add_node("rag", make_worker("rag"))
builder.add_node("live", make_worker("live"))
builder.add_node("aggregate", aggregate)

builder.add_edge(START, "dispatch")
# fan-out：从 dispatch 拉三条边到三个 worker → 它们在同一超步并行执行
builder.add_edge("dispatch", "web")
builder.add_edge("dispatch", "rag")
builder.add_edge("dispatch", "live")
# fan-in：三个 worker 都连到 aggregate → aggregate 等三个全部完成才执行
builder.add_edge("web", "aggregate")
builder.add_edge("rag", "aggregate")
builder.add_edge("live", "aggregate")
builder.add_edge("aggregate", END)

graph = builder.compile()


if __name__ == "__main__":
    t0 = time.time()
    result = graph.invoke({"query": "今天有什么比赛", "results": []})
    cost = time.time() - t0
    print(f"\n最终 results = {result['results']}")
    print(f"总耗时 {cost:.2f}s（三路各 0.5s：串行应约 1.5s，并行约 0.5s）")
