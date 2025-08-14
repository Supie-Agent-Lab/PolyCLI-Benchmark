from polycli.agent import ClaudeAgent, OpenSourceAgent

worker = OpenSourceAgent()

result0 = worker.run("Create a folder called interesting number stories. Write stories for numbers 50-100. First, make a plan.", model="glm-4.5", cli="qwen-code")
print(result0)

for i in range(100):
    if i % 3 == 0:
        result2 = worker.run(f"Evaluate the task's progress critically. Give suggestions and decisions. This is round {i}/100.", system_prompt="Your task is to keep the agent back on the correct track. Be rigorious, constructive. And be critical to the agent's false judements like false task completion claim.", model="glm-4.5", cli="qwen-code")
        print(result2)
    result1 = worker.run("continue the implementation", model="glm-4.5", cli="qwen-code")
    print(result1)

