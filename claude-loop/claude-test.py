from polycli.agent import ClaudeAgent

agent = ClaudeAgent()

print(
    agent.run("write a helloworld.py file. Then write a helloagain.py file.")
)
