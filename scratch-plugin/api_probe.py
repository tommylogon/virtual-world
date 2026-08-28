import fastmcp, inspect
from fastmcp import FastMCP
print("fastmcp version:", getattr(fastmcp, "__version__", "?"))
print("has run_tool:", hasattr(FastMCP, "run_tool"))
mcp = FastMCP("x")

@mcp.tool()
def hello(name: str) -> str:
    return "hi " + name

t = mcp.get_tool("hello")
print("get_tool returns:", type(t))
if t is not None:
    print("has fn:", hasattr(t, "fn"), "| has call:", hasattr(t, "call"))
print("coroutine?", inspect.iscoroutine(t))
