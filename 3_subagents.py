"""
Example 3: Subagents

Subagents are specialized agents the main agent can delegate tasks to.
Define them with AgentDefinition and grant the main agent the "Agent" tool.

Good for: parallelizing work, isolating concerns, or applying domain expertise.
"""

import anyio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ResultMessage,
    SystemMessage,
)


async def main():
    async for message in query(
        prompt=(
            "I have a Python project. Please use the code-reviewer to review agent.py "
            "for quality issues, and the summarizer to give me a one-sentence summary "
            "of what it does."
        ),
        options=ClaudeAgentOptions(
            cwd="/Users/phnorwood/Git/claude-agent-intro",
            # The main agent needs the Agent tool to spawn subagents
            allowed_tools=["Read", "Glob", "Agent"],
            agents={
                "code-reviewer": AgentDefinition(
                    description="Expert Python code reviewer. Checks for quality, clarity, and best practices.",
                    prompt=(
                        "You are a senior Python engineer. Review the provided code for: "
                        "1) correctness, 2) clarity, 3) best practices. "
                        "Be concise — bullet points only."
                    ),
                    tools=["Read"],
                ),
                "summarizer": AgentDefinition(
                    description="Summarizes what a file or piece of code does in one sentence.",
                    prompt="You are a technical writer. Summarize the provided code in exactly one sentence.",
                    tools=["Read"],
                ),
            },
        ),
    ):
        if isinstance(message, SystemMessage) and message.subtype == "init":
            print(f"Session: {message.session_id}")
        elif isinstance(message, ResultMessage):
            print(f"\n{message.result}")


anyio.run(main)
