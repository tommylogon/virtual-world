import asyncio
import fastmcp
from fastmcp import FastMCP
mcp = FastMCP("x")

@mcp.tool()
def hello(name: str) -> str:
    return "hi " + name

async def main():
    t = await mcp.get_tool("hello")
    print("await get_tool ->", type(t))
    print("attrs:", [a for a in dir(t) if not a.startswith("_")][:20])
    # try calling
    try:
        out = await t(name="world")
        print("call result:", out)
    except Exception as e:
        print("call err:", e)
    # try .fn
    if hasattr(t, "fn"):
        print("fn result:", t.fn(name="world"))

asyncio.run(main())
