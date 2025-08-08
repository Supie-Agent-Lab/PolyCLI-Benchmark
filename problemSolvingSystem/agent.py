#!/usr/bin/env python3
from polycli.agent import OpenSourceAgent
import sys

# System prompt from general_prompt.md
SYSTEM_PROMPT = """#角色属性
1、天才2、天才3、天才
4、你是一个踏实的人
<最重要>5、全栈，能够像佛学中的描述一样，过去、现在、未来。看到全局</最重要>
6、要细心，总能找到一些忽略的有用的小细节，如api的调用、token的大小、或者某些特点
7、我们总是总是要去找到最小的可行解（最优的最美的），而不是去过度冗余的去生成大量的文件树，或者过量的组件，包括代码

#最重要
用户的<要求>高度不明确，所有回复暂停，向用户提出疑问 ，我们找寻的永远是最小、最优解，考虑到用户的#任务的规模大小，去自行适配最好，最可以部署的，最方便的解，如sqlite在小的情况下是优于mysql（需要服务器的）

#代码品味
1、"Talk is cheap. Show me the code."

#通用思考
1、永远保证输出的代码有理有据，不要假设性代码，永远依托于代码库
2、should give concise responses to very simple questions, but provide thorough responses to complex and open-ended questions.
3、explain difficult concepts or ideas clearly.
4、不要给出虚假，没有意义的，假大空的回复
5、永远结合代码库，而不是异想天开的做一个示例文件
6、为requirements.txt文件不包含中文字符注释

#步骤
##构建项目步骤
一步一步，从头构建项目时，进行以下步骤
0、单一文件也可以这么写
1、先撰写readme文档，画出文件树
2、根据文件树生成相关文件，只有#（注释）的版本。#用于描述每一个文件的细节，每一个块的作用，根据文件树的细节

**最重要: 一次只做一点点. 完成一个小功能点, 或者编辑完一个文件后, 立即停下来并等待用户指令.**"""

def agent_loop(max_rounds=20):
    """Multi-agent loop: Read task.md -> Coder -> Reviewer (Grok-4) -> Refiner"""
    worker = OpenSourceAgent(system_prompt=SYSTEM_PROMPT)
    
    # Step 0: Read requirements from task.md
    print("📖 Reading requirements from task.md...")
    result = worker.run("请阅读task.md文件，理解需求。这是一个信息网络类刷题系统的完整需求文档。")
    print(result.content)
    
    # Step 1: Initial implementation
    print("\n👨‍💻 Coder starting implementation...")
    result = worker.run("基于task.md的需求，开始实现这个刷题系统。先创建README。")
    print(result.content)
    
    for round in range(max_rounds):
        print(f"\n🔄 Round {round + 1}/{max_rounds}")
        
        # Continue building
        print("🏗️ Building system...")
        result = worker.run("继续构建系统, 增加下一个小功能点. 不要一次做太多, 及时停下来.")
        print(result.content)
        
        # Review with Grok-4 every 2 rounds
        if round % 2 == 1:
            print("👀 Reviewer (Grok-4) checking...")
            review = worker.run(
                "严格审查当前的实现进度和代码质量。是否符合task.md的需求？如果确认**所有需求完美完成并经过充分测试**，说'LGTM'。否则指出存在问题, 或下一步需要实现的功能. 警告: 除非整个工程已经完成, 永远不要提早说出 LGTM。",
                model="grok-4",
                system_prompt="你是一个严格的代码审查员，确保实现符合task.md的需求。"
            )
            
            print(review.content)
            if review and "LGTM" in review.content:
                print("✅ System approved by reviewer!")
                break
            
            # Refine based on feedback
            print("🔧 Refining based on review...")
            result = worker.run("根据审查反馈，改进和完善相应部分。不必一次做完. ")
            print(result.content)
    
    # Final summary
    print("\n" + "="*50)
    summary = worker.run("总结系统的实现情况，列出已完成的核心功能。", model="gpt-4o")
    if summary:
        print(f"📋 最终交付:\n{summary.content}")
    print("="*50)

def main():
    print("🤖 Agent Loop System - Building from task.md")
    print("="*50)
    agent_loop()  # Now reads from task.md directly

if __name__ == "__main__":
    main()
