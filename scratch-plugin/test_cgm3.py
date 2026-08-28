import asyncio, sys
sys.path.insert(0, r"F:\AI\viwo\virtual-world\tools")
import code_graph_mcp as cg

async def call(tool_name, **kw):
    tool = await cg.mcp.get_tool(tool_name)
    return tool.fn(**kw)

async def main():
    print("=== search_code ===")
    print(await call("search_code", query="where is carry weight enforced", top_k=5))
    print()
    print("=== search_keywords ===")
    print(await call("search_keywords", query="vector_store", top_k=5))
    print()
    print("=== code_callers ===")
    print(await call("code_callers", name="tick_turn"))

asyncio.run(main())
