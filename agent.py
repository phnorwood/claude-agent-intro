import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def main():
    async for message in query(
        prompt="List the files in the current directory and briefly describe what this project does.",
        options=ClaudeAgentOptions(
            cwd="/Users/phnorwood/Git/claude-agent-intro",
            allowed_tools=["Read", "Glob", "Bash"],
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


anyio.run(main)
