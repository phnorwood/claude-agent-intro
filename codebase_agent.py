"""
Codebase Q&A Agent
------------------
A Claude-powered agent that navigates and answers questions about any codebase.

HOW IT WORKS:
  1. You point it at a directory and ask a question
  2. Claude decides which files to look at (using tools you define)
  3. It reads files, searches for patterns, and builds understanding
  4. It loops — gathering context → forming an answer → reading more if needed
  5. When Claude is confident, it returns a final answer

SETUP:
  pip install anthropic
  export ANTHROPIC_API_KEY=your_key_here

USAGE:
  python codebase_agent.py --path ./my_project --question "Where is auth handled?"
  python codebase_agent.py --path ./my_project --question "What does the payment module do?"
  python codebase_agent.py  # uses current directory, prompts for question
"""

import os
import json
import fnmatch
import argparse
import anthropic

# ──────────────────────────────────────────────
# TOOL DEFINITIONS
# These tell Claude what capabilities it has.
# Claude will decide when and how to call them.
# ──────────────────────────────────────────────

TOOLS = [
    {
        "name": "list_directory",
        "description": (
            "List files and folders in a directory. Use this to orient yourself "
            "and discover the structure of the codebase before diving into files."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to list (e.g. '.' for root, 'src/utils')"
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Whether to include hidden files (default: false)"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "read_file",
        "description": (
            "Read the full contents of a file. Use this to understand what a specific "
            "file does. Prefer reading smaller files first to orient yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file (e.g. 'src/auth.py')"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_in_files",
        "description": (
            "Search for a keyword or pattern across all files in the codebase. "
            "Returns filenames and matching lines. Use this to quickly find where "
            "something is defined or used without reading every file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text or keyword to search for (case-insensitive)"
                },
                "file_extension": {
                    "type": "string",
                    "description": "Optional: limit search to files with this extension (e.g. '.py', '.js')"
                }
            },
            "required": ["pattern"]
        }
    }
]


# ──────────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# The actual Python code that runs when Claude
# calls each tool.
# ──────────────────────────────────────────────

# Files/dirs to always skip (keeps context clean)
IGNORE_PATTERNS = [
    "*.pyc", "__pycache__", ".git", "node_modules",
    ".venv", "venv", "*.egg-info", ".DS_Store",
    "dist", "build", "*.lock", "*.log"
]

def should_ignore(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in IGNORE_PATTERNS)


def tool_list_directory(path: str, show_hidden: bool = False) -> str:
    """List contents of a directory relative to the codebase root."""
    full_path = os.path.join(CODEBASE_ROOT, path)
    if not os.path.exists(full_path):
        return f"Error: path '{path}' does not exist."

    entries = []
    try:
        for name in sorted(os.listdir(full_path)):
            if not show_hidden and name.startswith("."):
                continue
            if should_ignore(name):
                continue
            item_path = os.path.join(full_path, name)
            kind = "DIR " if os.path.isdir(item_path) else "FILE"
            size = ""
            if os.path.isfile(item_path):
                size = f"  ({os.path.getsize(item_path):,} bytes)"
            entries.append(f"  [{kind}] {name}{size}")
    except PermissionError:
        return f"Error: permission denied for '{path}'"

    if not entries:
        return f"Directory '{path}' is empty."
    return f"Contents of '{path}':\n" + "\n".join(entries)


def tool_read_file(path: str) -> str:
    """Read a file's contents, with a size guard to avoid massive files."""
    full_path = os.path.join(CODEBASE_ROOT, path)
    if not os.path.exists(full_path):
        return f"Error: file '{path}' does not exist."
    if not os.path.isfile(full_path):
        return f"Error: '{path}' is a directory, not a file."

    size = os.path.getsize(full_path)
    MAX_BYTES = 50_000  # ~50KB — enough for most source files
    if size > MAX_BYTES:
        return (
            f"File '{path}' is large ({size:,} bytes). "
            f"Showing first {MAX_BYTES:,} bytes:\n\n"
            + open(full_path, "r", errors="replace").read(MAX_BYTES)
            + "\n\n[...file truncated. Use search_in_files to find specific sections.]"
        )

    try:
        with open(full_path, "r", errors="replace") as f:
            content = f.read()
        return f"Contents of '{path}':\n\n{content}"
    except Exception as e:
        return f"Error reading '{path}': {e}"


def tool_search_in_files(pattern: str, file_extension: str = None) -> str:
    """Walk the codebase and find files containing the pattern."""
    matches = []
    pattern_lower = pattern.lower()

    for dirpath, dirnames, filenames in os.walk(CODEBASE_ROOT):
        # Prune ignored directories in-place
        dirnames[:] = [d for d in dirnames if not should_ignore(d)]

        for filename in filenames:
            if should_ignore(filename):
                continue
            if file_extension and not filename.endswith(file_extension):
                continue

            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, CODEBASE_ROOT)

            try:
                with open(filepath, "r", errors="replace") as f:
                    lines = f.readlines()
            except Exception:
                continue

            file_matches = []
            for i, line in enumerate(lines, 1):
                if pattern_lower in line.lower():
                    file_matches.append(f"  Line {i:4d}: {line.rstrip()}")

            if file_matches:
                matches.append(f"\n{rel_path}:")
                matches.extend(file_matches[:10])  # cap per-file results
                if len(file_matches) > 10:
                    matches.append(f"  ... and {len(file_matches) - 10} more matches")

    if not matches:
        return f"No matches found for '{pattern}'."

    total = len([m for m in matches if not m.startswith("\n") and not m.startswith("  ...")])
    header = f"Found matches for '{pattern}' ({total} lines across {matches.count(chr(10))} files):"
    return header + "".join(matches)


# ──────────────────────────────────────────────
# TOOL DISPATCHER
# Routes Claude's tool calls to the right function
# ──────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name and return the result as a string."""
    print(f"  → [{tool_name}] {json.dumps(tool_input)}")

    if tool_name == "list_directory":
        return tool_list_directory(
            tool_input["path"],
            tool_input.get("show_hidden", False)
        )
    elif tool_name == "read_file":
        return tool_read_file(tool_input["path"])
    elif tool_name == "search_in_files":
        return tool_search_in_files(
            tool_input["pattern"],
            tool_input.get("file_extension")
        )
    else:
        return f"Error: unknown tool '{tool_name}'"


# ──────────────────────────────────────────────
# AGENT LOOP
# This is the heart of the agent. It calls Claude,
# handles tool use, and loops until Claude is done.
# ──────────────────────────────────────────────

def run_agent(question: str) -> str:
    """
    Run the Q&A agent on a question about the codebase.

    The loop:
      1. Send question + tools to Claude
      2. If Claude calls a tool → execute it, append result, go to 1
      3. If Claude says end_turn → return the final answer
    """
    client = anthropic.Anthropic()

    system_prompt = f"""You are a senior software engineer helping a developer understand a codebase.

The codebase root is: {CODEBASE_ROOT}

Your job:
- Use the tools to explore and understand the code
- Start broad (list_directory on '.') to understand the structure
- Then narrow down with search_in_files or read_file as needed
- Answer the developer's question thoroughly, citing specific files and line numbers
- Be concise but complete — explain *why* things work, not just *where* they are

Guidelines:
- Don't read every file — be strategic. Search first, then read relevant files.
- If a file is very large, use search_in_files to find the relevant section first.
- When you have enough context to answer confidently, stop exploring and give the answer.
"""

    messages = [{"role": "user", "content": question}]

    print(f"\nQuestion: {question}")
    print(f"Codebase: {CODEBASE_ROOT}")
    print("─" * 60)
    print("Agent working...\n")

    iteration = 0
    MAX_ITERATIONS = 20  # safety limit — prevents runaway loops

    while iteration < MAX_ITERATIONS:
        iteration += 1

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )

        # Append Claude's response to conversation history
        messages.append({"role": "assistant", "content": response.content})

        # ── Case 1: Claude is done ──
        if response.stop_reason == "end_turn":
            final_text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "No response generated."
            )
            return final_text

        # ── Case 2: Claude wants to use tools ──
        elif response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Feed all tool results back to Claude in one message
            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason
            break

    return "Agent reached maximum iterations without a final answer. Try a more specific question."


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

def main():
    global CODEBASE_ROOT

    parser = argparse.ArgumentParser(description="Ask questions about a codebase using Claude.")
    parser.add_argument("--path", default=".", help="Path to the codebase (default: current directory)")
    parser.add_argument("--question", default=None, help="Question to ask about the codebase")
    args = parser.parse_args()

    CODEBASE_ROOT = os.path.abspath(args.path)

    if not os.path.isdir(CODEBASE_ROOT):
        print(f"Error: '{CODEBASE_ROOT}' is not a valid directory.")
        return

    question = args.question
    if not question:
        question = input("What do you want to know about this codebase?\n> ").strip()
        if not question:
            print("No question provided.")
            return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Get your key at https://console.anthropic.com")
        return

    answer = run_agent(question)

    print("\n" + "─" * 60)
    print("ANSWER\n")
    print(answer)
    print("─" * 60)


if __name__ == "__main__":
    CODEBASE_ROOT = "."  # default, overridden in main()
    main()
