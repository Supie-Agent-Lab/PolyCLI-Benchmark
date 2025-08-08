from polycli.agent import ClaudeAgent, OpenSourceAgent

worker = OpenSourceAgent()

result0 = worker.run("Overall task: create a text based command line game. Has an interesting main story. The game sould have extensive content.", model="glm-4.5", cli="mini-swe")
print(result0)

for i in range(100):
    if i % 3 == 0:
        result2 = worker.run(f"Evaluate the task's progress critically. Give suggestions and decisions. This is round {i}/100.", system_prompt="Your task is to keep the agent back on the correct track. Be rigorious, constructive. And be critical to the agent's false judements like false task completion claim.", model="glm-4.5", cli="no-tools")
        print(result2)
    result1 = worker.run("Continue to build the game.", model="glm-4.5", cli="mini-swe")
    print(result1)

