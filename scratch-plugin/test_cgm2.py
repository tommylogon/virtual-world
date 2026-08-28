import sys
sys.path.insert(0, r"F:\AI\viwo\virtual-world\tools")
import code_graph_mcp as cg

def call(name, **kw):
    tool = cg.mcp.get_tool(name)
    return tool.fn(**kw)

print("=== search_code ===")
print(call("search_code", query="where is carry weight enforced", top_k=5))
print()
print("=== search_keywords ===")
print(call("search_keywords", query="vector_store", top_k=5))
print()
print("=== code_callers ===")
print(call("code_callers", name="tick_turn"))
print()
print("=== graph_stats ===")
print(call("graph_stats"))
