"""
Example 4: Permission Modes

Permission modes control how the agent handles potentially dangerous operations.
Choose the right mode for your use case.

Modes:
  "default"           — Prompts the user before dangerous operations (safe default)
  "plan"              — Agent produces a plan but does NOT execute anything
  "acceptEdits"       — Auto-accepts file reads/writes; prompts for Bash/destructive ops
  "dontAsk"           — Skips all prompts (good for CI/CD; still enforces allowed_tools)
  "bypassPermissions" — Skips all safety checks (requires allow_dangerously_skip_permissions=True)
"""

import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


# --- Mode 1: default ---
# Use during development when you want to review each action.
async def run_default_mode():
    print("=== default mode: will prompt before dangerous ops ===")
    async for message in query(
        prompt="List Python files in the current directory.",
        options=ClaudeAgentOptions(
            cwd="/Users/phnorwood/Git/claude-agent-intro",
            allowed_tools=["Glob"],
            permission_mode="default",
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


# --- Mode 2: plan ---
# Agent thinks through the task and describes what it would do — no execution.
async def run_plan_mode():
    print("\n=== plan mode: describes actions without executing them ===")
    async for message in query(
        prompt="Refactor agent.py to add error handling around the anyio.run() call.",
        options=ClaudeAgentOptions(
            cwd="/Users/phnorwood/Git/claude-agent-intro",
            allowed_tools=["Read", "Edit"],
            permission_mode="plan",
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


# --- Mode 3: acceptEdits ---
# File reads/writes are auto-approved; Bash commands still require confirmation.
# Good for automated refactoring pipelines.
async def run_accept_edits_mode():
    print("\n=== acceptEdits mode: file edits auto-approved ===")
    async for message in query(
        prompt="Add a docstring to the main() function in agent.py.",
        options=ClaudeAgentOptions(
            cwd="/Users/phnorwood/Git/claude-agent-intro",
            allowed_tools=["Read", "Edit"],
            permission_mode="acceptEdits",
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


# --- Mode 4: bypassPermissions ---
# Skips ALL prompts. Use only in sandboxed/CI environments you fully control.
async def run_bypass_mode():
    print("\n=== bypassPermissions mode: no prompts at all ===")
    async for message in query(
        prompt="Create a file called ci_output.txt with the text 'CI run complete.'",
        options=ClaudeAgentOptions(
            cwd="/Users/phnorwood/Git/claude-agent-intro",
            allowed_tools=["Write"],
            permission_mode="bypassPermissions",
            allow_dangerously_skip_permissions=True,  # required for bypass
        ),
    ):
        if isinstance(message, ResultMessage):
            print(message.result)


async def main():
    await run_default_mode()
    await run_plan_mode()
    await run_accept_edits_mode()
    await run_bypass_mode()


anyio.run(main)
