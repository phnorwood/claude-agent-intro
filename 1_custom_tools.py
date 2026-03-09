"""
Example 1: Custom Tools via MCP Server

Define your own tools that the agent can call. Tools are exposed via an
in-process MCP server and passed to the agent through mcp_servers.
"""

import anyio
from claude_agent_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)


# Define custom tools with @tool(name, description, input_schema)
@tool("get_weather", "Get the current weather for a city", {"city": str})
async def get_weather(args):
    city = args["city"]
    # Replace with a real weather API call
    return {"content": [{"type": "text", "text": f"The weather in {city} is sunny and 72°F."}]}


@tool("get_population", "Get the population of a city", {"city": str})
async def get_population(args):
    populations = {
        "Paris": "2.1 million",
        "London": "9 million",
        "Tokyo": "14 million",
    }
    city = args["city"]
    pop = populations.get(city, "unknown")
    return {"content": [{"type": "text", "text": f"The population of {city} is {pop}."}]}


async def main():
    server = create_sdk_mcp_server("my-tools", tools=[get_weather, get_population])

    options = ClaudeAgentOptions(mcp_servers={"my-tools": server})

    async with ClaudeSDKClient(options=options) as client:
        await client.query("What's the weather and population of Paris and Tokyo?")
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)


anyio.run(main)
