"""Example PolyCLI sandbox entry."""

from polycli import PolyAgent
from pathlib import Path

# Read input
input_file = Path("input/sample.txt")
if input_file.exists():
    data = input_file.read_text()
    print(f"Read input: {data}")

# Process with agent
agent = PolyAgent()
result = agent.run(f"Summarize this: {data}")
print(f"Agent response: {result.content}")

result = agent.run(f"What's your opinion?")
print(f"Agent response: {result.content}")

# Write output
output_file = Path("output/summary.txt")
output_file.write_text(result.content)
print(f"Wrote output to {output_file}")
