#!/usr/bin/env python3
from polycli.agent import OpenSourceAgent
from pydantic import BaseModel, Field
from typing import List, Optional
import sys

# Pydantic model for structured review output
class ReviewResult(BaseModel):
    """Structured review result to prevent accidental LGTM"""
    is_complete: bool = Field(description="是否所有需求都已完美完成并经过充分测试")
    completion_percentage: int = Field(description="完成度百分比（0-100）", ge=0, le=100)
    issues: List[str] = Field(description="存在的问题列表，如果没有问题则为空列表")
    next_steps: List[str] = Field(description="下一步需要实现的功能列表")
    critical_issues: Optional[str] = Field(description="关键问题（如果有）", default=None)
    
    def should_continue(self) -> bool:
        """判断是否应该继续开发"""
        return not self.is_complete or self.completion_percentage < 95

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
    worker = OpenSourceAgent(system_prompt=SYSTEM_PROMPT, debug=True)
    
    # Step 0: Read requirements from task.md
    print("📖 Reading requirements from task.md...")
    result = worker.run("请阅读task.md文件，理解需求。这是一个信息网络类刷题系统的完整需求文档。")
    print(result.content)
    
    # Step 1: Initial implementation
    print("\n👨‍💻 Coder starting implementation...")
    result = worker.run("基于task.md的需求，开始实现这个刷题系统。先创建README。注意包括 README 的所有项目文件都应该放在 putYourPojectHere 子文件下.")
    print(result.content)
    
    for round in range(max_rounds):
        print(f"\n🔄 Round {round + 1}/{max_rounds}")
        
        # Debug: Save messages to JSON file
        import json
        from pathlib import Path
        debug_dir = Path("debug_messages")
        debug_dir.mkdir(exist_ok=True)
        
        # Save messages before running
        messages_file = debug_dir / f"round_{round+1:02d}_before.json"
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(worker.messages, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved messages to {messages_file}")
        
        # Debug: Print ALL messages
        print(f"\n📝 Total messages: {len(worker.messages)}")
        print("=" * 50)
        for i, msg in enumerate(worker.messages):
            role = msg.get('role', 'unknown')
            # Handle different message formats
            if 'parts' in msg:
                # Qwen format
                parts = msg.get('parts', [])
                if parts and isinstance(parts[0], dict):
                    content = str(parts[0].get('text', 'no text'))[:200]
                else:
                    content = str(parts)[:200]
            else:
                # Simple format
                content = str(msg.get('content', 'no content'))[:200]
            print(f"[{i}] {role}: {content}...")
        print("=" * 50)
        
        # Continue building
        print("🏗️ Building system...")
        result = worker.run("继续构建系统, 增加下一个小功能点. 不要一次做太多, 及时停下来.")
        print(result.content)
        
        # Save messages after running
        messages_file_after = debug_dir / f"round_{round+1:02d}_after.json"
        with open(messages_file_after, 'w', encoding='utf-8') as f:
            json.dump(worker.messages, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved messages after to {messages_file_after}")
        
        # Also save the raw result
        result_file = debug_dir / f"round_{round+1:02d}_result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "content": result.content,
                "is_success": result.is_success,
                "raw_result": result.raw_result,
                "error_message": result.error_message
            }, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved result to {result_file}")
        
        # Review with Grok-4 every 2 rounds
        if round % 2 == 1:
            print("👀 Reviewer (glm-4.5) checking with structured output...")
            review = worker.run(
                """严格审查当前的实现进度和代码质量，对照task.md的需求。
                请仔细评估：
                1. 所有功能是否都已实现？
                2. 代码质量如何？
                3. 是否有测试？
                4. 还有哪些需要完成的工作？
                
                警告: 只有当整个工程100%完成时，is_complete才能为true。""",
                model="glm-4.5",
                system_prompt="你是一个严格的代码审查员，确保实现符合task.md的需求。",
                cli="no-tools",  # Use no-tools mode for structured output
                schema_cls=ReviewResult
            )
            
            # Debug: Save review result and messages
            review_result_file = debug_dir / f"round_{round+1:02d}_review_result.json"
            with open(review_result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "content": review.content if review else None,
                    "is_success": review.is_success if review else False,
                    "raw_result": review.raw_result if review else None,
                    "has_data": review.has_data() if review else False,
                    "data": review.data if review and review.data else None
                }, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved review result to {review_result_file}")
            
            # Save messages after review
            messages_file_after_review = debug_dir / f"round_{round+1:02d}_after_review.json"
            with open(messages_file_after_review, 'w', encoding='utf-8') as f:
                json.dump(worker.messages, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved messages after review to {messages_file_after_review}")
            
            # Debug: Print messages after review
            print(f"\n📝 After review - Total messages: {len(worker.messages)}")
            if len(worker.messages) > 0:
                last_msg = worker.messages[-1]
                role = last_msg.get('role', 'unknown')
                if 'parts' in last_msg:
                    parts = last_msg.get('parts', [])
                    if parts and isinstance(parts[0], dict):
                        content = str(parts[0].get('text', 'no text'))[:300]
                    else:
                        content = str(parts)[:300]
                else:
                    content = str(last_msg.get('content', 'no content'))[:300]
                print(f"Last message - {role}: {content}...")
            
            review_data = None
            if review and review.data:
                review_data = ReviewResult(**review.data)
                print(f"📊 完成度: {review_data.completion_percentage}%")
                print(f"✅ 是否完成: {review_data.is_complete}")
                if review_data.issues:
                    print(f"❌ 问题: {', '.join(review_data.issues[:3])}")
                if review_data.next_steps:
                    print(f"📝 下一步: {', '.join(review_data.next_steps[:3])}")
                
                if review_data.is_complete and review_data.completion_percentage >= 95:
                    print("✅ System approved by reviewer! All requirements completed!")
                    break
            else:
                print("⚠️ Failed to get structured review result")
                continue
            
            # Refine based on feedback
            if review_data and review_data.should_continue():
                print("🔧 Refining based on review...")
                
                # Build specific refine prompt based on review data
                refine_prompt = "根据审查反馈，需要改进以下方面：\n"
                if review_data.critical_issues:
                    refine_prompt += f"关键问题：{review_data.critical_issues}\n"
                if review_data.issues:
                    refine_prompt += f"问题：{', '.join(review_data.issues[:3])}\n"
                if review_data.next_steps:
                    refine_prompt += f"下一步：{review_data.next_steps[0]}\n"
                refine_prompt += "请处理最重要的问题，不必一次做完。"
                
                refine_result = worker.run(refine_prompt)
                print(refine_result.content if refine_result else "No refine result!")
    
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
