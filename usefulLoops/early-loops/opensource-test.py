from polycli.agent import OpenSourceAgent

agent = OpenSourceAgent()

print(
    agent.run("write a helloworld.py file. Then write a helloagain.py file.", model="glm-4.5")
)

