#!/usr/bin/env python3
"""Simple test to debug the agent response issue"""

from polycli import PolyAgent

# Test 1: Direct API call
print("Test 1: Direct API call (no CLI)")
agent1 = PolyAgent(id="test1", debug=True)
result1 = agent1.run("Say hello", cli=False)  # Force API mode
print(f"Result 1: {result1}")
print(f"Content: {result1.content if result1 else 'None'}")

print("\n" + "="*50 + "\n")

# Test 2: With claude-code CLI
print("Test 2: With claude-code CLI")
agent2 = PolyAgent(id="test2", debug=True)
result2 = agent2.run("Say hello", cli="claude-code")
print(f"Result 2: {result2}")
print(f"Content: {result2.content if result2 else 'None'}")

print("\n" + "="*50 + "\n")

# Test 3: Auto CLI selection
print("Test 3: Auto CLI selection")
agent3 = PolyAgent(id="test3", debug=True)
result3 = agent3.run("Say hello")
print(f"Result 3: {result3}")
print(f"Content: {result3.content if result3 else 'None'}")