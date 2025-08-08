from polycli.agent import ClaudeAgent

agent = ClaudeAgent()

print(
    agent.run("hello", model="grok-4")
)
