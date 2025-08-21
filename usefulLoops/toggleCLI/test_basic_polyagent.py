#!/usr/bin/env python3
"""Basic test for PolyAgent with simple math query"""

from polycli.polyagent import PolyAgent

# Create agent
agent = PolyAgent(debug=True)

# Test: Simple math query
print("=== Basic Math Test ===")
response = agent.run("What is 2+2?")
print("Response:", response.content)
print("Success:", response.is_success)
if response.get_claude_cost():
    print(f"Cost: ${response.get_claude_cost()}")