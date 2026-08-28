import asyncio, sys
sys.path.insert(0, r"F:\AI\viwo\virtual-world\tools")
import code_graph_mcp as cg

async def main():
    tool = await cg.mcp.get_tool("search_keywords")
    print("### query: vector_store")
    print(tool.fn(query="vector_store", top_k=5))
    print()
    print("### query: store")
    print(tool.fn(query="store", top_k=5))
    print()
    print("### query: carry weight")
    print(tool.fn(query="carry weight", top_k=5))

asyncio.run(main())
