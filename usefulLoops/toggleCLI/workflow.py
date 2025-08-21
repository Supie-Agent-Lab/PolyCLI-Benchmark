#!/usr/bin/env python3
"""Demonstrate unified agent workflow across different backends."""

from polycli import PolyAgent
from polycli.orchestration import session, serve_session, pattern

@pattern
def plan(agent: PolyAgent, task: str):
    """Use cheap API to plan the task."""
    prompt = f"Plan how to: {task}\nList 3 clear steps."
    result = agent.run(prompt, cli="no-tools")
    if not result:
        print(result)
    else:
        return result.content

@pattern
def analyze(agent: PolyAgent, file_path: str):
    """Use Qwen to read and analyze file."""
    prompt = f"Read {file_path} and summarize what parameters could be modified"
    result = agent.run(prompt, cli="claude-code")
    if not result:
        print(result)
    else:
        return result.content

@pattern
def implement(agent: PolyAgent, original_file: str, new_file: str, change: str):
    """Use Claude to create modified version."""
    prompt = f"Read {original_file} and create {new_file} with this change: {change}"
    result = agent.run(prompt, cli="qwen-code")
    if not result:
        print(result)
    else:
        return result.content

# Main workflow
agent = PolyAgent(id="unified", debug=True)

with session() as s:
    serve_session(s)
    
    plan(agent, "create a variant of test_basic_polyagent.py with different test values")
    analyze(agent, "test_basic_polyagent.py") 
    implement(agent, "test_basic_polyagent.py", "test_variant.py", "change 2+2 to 5+5")

print(agent.run("summarize our conversation so far", cli="claude-code", model="glm-4.5").content)
agent.save_state("agent.jsonl")
input()

