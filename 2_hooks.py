"""
Example 2: Hooks for Logging and Auditing

Hooks let you intercept tool calls before and after they execute.
Useful for logging, auditing, validation, or sending notifications.
"""

import anyio
from datetime import datetime
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, ResultMessage


# PreToolUse hook — runs before each tool call
# Return {"decision": "block", "reason": "..."} to prevent a tool from running.
async def log_before_tool(input_data, tool_use_id, context):
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    print(f"[{datetime.now():%H:%M:%S}] BEFORE {tool_name}: {tool_input}")
    return {}  # Allow the tool to proceed


# PostToolUse hook — runs after each tool call completes
async def log_after_tool(input_data, tool_use_id, context):
    tool_name = input_data.get("tool_name", "unknown")
    file_path = input_data.get("tool_input", {}).get("file_path", "")
    log_line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {tool_name} | {file_path or 'n/a'}\n"

    with open("audit.log", "a") as f:
        f.write(log_line)

    print(f"[{datetime.now():%H:%M:%S}] AFTER  {tool_name}")
    return {}


async def main():
    async for message in query(
        prompt="Create a file called hello.txt with the content 'Hello, world!' then read it back.",
        options=ClaudeAgentOptions(
            cwd="/Users/phnorwood/Git/claude-agent-intro",
            allowed_tools=["Write", "Read"],
            permission_mode="acceptEdits",
            hooks={
                # Run log_before_tool before ANY tool call
                "PreToolUse": [HookMatcher(matcher=".*", hooks=[log_before_tool])],
                # Run log_after_tool after Write or Read tool calls
                "PostToolUse": [HookMatcher(matcher="Write|Read", hooks=[log_after_tool])],
            },
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"\nResult: {message.result}")


anyio.run(main)
