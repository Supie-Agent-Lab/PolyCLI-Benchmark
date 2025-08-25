#!/usr/bin/env python3

from polycli import PolyAgent
from polycli.orchestration import session, pattern, serve_session
from polycli.builtin_patterns import notify, multi_head_write
from pathlib import Path

# No size limit for knowledge - let it grow as needed
max_retries = 6
AGENT_TOKEN_LIMIT = 180000  # 200k tokens per agent
CLI = "qwen-code"
CLI_model = "google/gemini-2.5-pro"

SAFETY_WARNING = """
IMPORTANT: Do NOT perform any dangerous operations. Do NOT edit or write any files. 
Only read and analyze. Your task is discovery and reporting only.
"""

QUIZ_QUALITY_GUIDANCE = """
Examples of good questions:
- "What specific error occurs when you wrap asyncio.sleep() in a tuple?"
- "Why does the WebSocket handshake fail with certain client versions?"
- "What's the race condition in device reconnection and how was it solved?"

Examples of bad questions:
- "What is WebSocket?"
- "How do you handle errors in Python?"
- "What is async programming?"

Generate 20-50% of the total issues as quiz questions.
Questions should be SPECIFIC - things you couldn't answer without actually working on this project.
"""

@pattern
def extract_knowledge_discovery(extractor: PolyAgent, blocks_dir: str):
    prompt = f"""Read all the block files in {blocks_dir} and discover CONCRETE and VALUABLE knowledge.

{SAFETY_WARNING}

Focus on:
- Specific technical solutions that worked
- Exact error patterns and their fixes
- Critical configuration values and settings
- Architectural decisions and their reasons
- Performance optimizations discovered
- Integration patterns that work
- Workarounds for specific bugs
- Important conventions and standards

Be SPECIFIC. Include:
- File paths and line numbers when relevant
- Exact error messages
- Code snippets that solve problems
- Configuration examples
- Command sequences that work

Give a comprehensive summary of all valuable knowledge discovered."""
    if CLI == "claude-code":
        result = extractor.run(prompt, tracked=True)
    else:
        result = extractor.run(prompt, cli=CLI, tracked=True, model=CLI_model)

    return result.content

@pattern
def generate_knowledge_md(extractor: PolyAgent):
    prompt = """Based on all the knowledge you've discovered, create a comprehensive knowledge.md file content.

Requirements:
- Must be specific enough to answer detailed technical questions
- Must include concrete examples, error messages, solutions
- Include code snippets, configuration examples, exact commands
- Document all patterns, workarounds, and fixes discovered

Structure it well with clear sections.
Focus on actionable, specific knowledge over general concepts.
Be as comprehensive as possible - this is our only chance to capture this knowledge."""
    
    # Use multi-head write for comprehensive output
    result = multi_head_write(
        extractor,
        prompt,
        model="google/gemini-2.5-pro",
        max_sections=8,  # Up to 8 sections
        section_token_limit=AGENT_TOKEN_LIMIT,
        verbose=True
    )
    
    if result.is_success:
        return result.content
    else:
        raise RuntimeError(f"Knowledge generation failed: {result.error_message}")

@pattern
def answer_quiz(answerer: PolyAgent, knowledge_content: str, quiz: str):
    prompt = f"""You have this knowledge base about a project:

KNOWLEDGE BASE:
{knowledge_content}

Answer this quiz using ONLY the knowledge provided above.
BE HONEST: If the information is not in the knowledge base, say "I don't know" - do not guess using general knowledge.

QUIZ:
{quiz}

Answer each question clearly and specifically.
If you don't have enough information, admit it."""
    
    for attempt in range(1, max_retries + 1):
        result = answerer.run(prompt, model="google/gemini-2.5-pro", cli="no-tools", ephemeral=True)
        if result.is_success:
            return result.content
        if attempt < max_retries:
            print(f"      Retry {attempt}/{max_retries - 1}: {result.error_message}")
    raise RuntimeError(f"Quiz answering failed after {max_retries} attempts: {result.error_message}")

@pattern
def score_answers(scorer: PolyAgent, pain_points: str, knowledge_content: str, quiz: str, answers: str):
    prompt = f"""Score these quiz answers strictly based on accuracy and completeness.

ORIGINAL PAIN POINTS (ground truth):
{pain_points}

KNOWLEDGE BASE USED:
{knowledge_content}

QUIZ:
{quiz}

ANSWERS PROVIDED:
{answers}

Score each answer:
- Correct and complete: 1.0
- Partially correct: 0.5
- Wrong or "I don't know": 0.0

Give:
1. Individual scores for each question
2. Overall score (average)
3. Directional suggestions for improvement (e.g., "needs more on WebSocket reconnection handling", "missing details about error recovery patterns")

Be STRICT. Only give full marks for accurate, specific answers."""
    
    for attempt in range(1, max_retries + 1):
        result = scorer.run(prompt, model="google/gemini-2.5-pro", cli="no-tools", ephemeral=False)
        if result.is_success:
            return result.content
        if attempt < max_retries:
            print(f"      Retry {attempt}/{max_retries - 1}: {result.error_message}")
    raise RuntimeError(f"Scoring failed after {max_retries} attempts: {result.error_message}")

@pattern
def extract_improvement_suggestions(scorer: PolyAgent):
    prompt = """You are the Knowledge Improvement Advisor in our iterative knowledge extraction system.

YOUR ROLE: Help build a comprehensive knowledge base that future AI agents can use to understand this codebase without starting from zero.

HOW THE SYSTEM WORKS:
1. An extractor agent reads code blocks and builds a knowledge.md file
2. A quiz agent generates technical questions from pain points
3. An answerer agent (with ONLY the knowledge.md) tries to answer
4. You score the answers and identify knowledge gaps
5. The extractor uses your suggestions to improve the knowledge.md
6. This repeats for 5 rounds total

YOUR JOB NOW: Based on the quiz answers you just scored, generate LONG, detailed suggestions for what knowledge to add.

Write at least 1000 words covering:
- Specific technical areas where answers were weak or missing
- Types of error patterns, fixes, and workarounds to document
- Configuration values, settings, and their implications
- Architectural decisions and why they matter
- Performance bottlenecks and optimizations discovered
- Integration patterns, compatibility issues, version-specific behaviors
- Command sequences, debugging techniques, solution patterns
- Edge cases, gotchas, and non-obvious behaviors

IMPORTANT: Your goal is comprehensive knowledge extraction, not just quiz answers.
Some reference to quiz topics is fine to guide extraction, but avoid overfitting.
Think broadly - what knowledge would help ANY future agent working on this codebase?

Be specific and actionable. Tell the extractor exactly what kinds of information to look for and extract."""
    
    for attempt in range(1, max_retries + 1):
        result = scorer.run(prompt, model="google/gemini-2.5-pro", cli="no-tools", ephemeral=False)
        if result.is_success:
            return result.content
        if attempt < max_retries:
            print(f"      Retry {attempt}/{max_retries - 1}: {result.error_message}")
    raise RuntimeError(f"Scoring failed after {max_retries} attempts: {result.error_message}")

@pattern
def generate_quiz(quiz_agent: PolyAgent, pain_points_content: str, previous_quiz: str = None):
    if previous_quiz:
        prompt = f"""Generate a NEW quiz based on these pain points, avoiding repetition.

PREVIOUS QUIZ (DO NOT REPEAT):
{previous_quiz}

PAIN POINTS:
{pain_points_content}

{QUIZ_QUALITY_GUIDANCE}

Output format:
1. [Question]
2. [Question]
..."""
    else:
        prompt = f"""Generate a quiz based on these pain points.

PAIN POINTS:
{pain_points_content}

{QUIZ_QUALITY_GUIDANCE}

Output format:
1. [Question]
2. [Question]
..."""
    
    for attempt in range(1, max_retries + 1):
        result = quiz_agent.run(prompt, model="google/gemini-2.5-pro", cli="no-tools", ephemeral=True)
        if result.is_success:
            return result.content
        if attempt < max_retries:
            print(f"      Retry {attempt}/{max_retries - 1}: {result.error_message}")
    raise RuntimeError(f"Quiz generation failed after {max_retries} attempts: {result.error_message}")

def main():
    workspace = Path("workspace")
    blocks_base_dir = workspace / "blocks"
    pain_points_base_dir = workspace / "pain_points"
    knowledge_dir = workspace / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    
    # Find all persona directories
    persona_dirs = [d for d in pain_points_base_dir.iterdir() if d.is_dir()]
    if not persona_dirs:
        print("No pain point directories found. Run stage2 first.")
        return
    
    with session() as s:
        server, _ = serve_session(s, port=8766)
        print(f"Monitor at http://localhost:8766\n")
        
        # Process each persona separately
        for persona_dir in persona_dirs:
            persona_name = persona_dir.name
            print(f"\n{'='*60}")
            print(f"Processing persona: {persona_name}")
            print(f"{'='*60}")
            
            blocks_dir = blocks_base_dir / persona_name
            pain_points_dir = pain_points_base_dir / persona_name
            
            # Load all pain points for this persona
            merged_files = sorted(pain_points_dir.glob("*/merged_pain_points.md"))
            all_pain_points = ""
            for f in merged_files:
                all_pain_points += f.read_text(encoding='utf-8') + "\n\n---\n\n"
            
            print(f"Loaded {len(merged_files)} merged pain point files")
            print(f"Total pain points: {len(all_pain_points)} characters")
            
            if not merged_files or not all_pain_points:
                print(f"ERROR: No pain points found for {persona_name}. Skipping...")
                continue
            
            extractor = PolyAgent(id=f"knowledge_extractor_{persona_name}", max_tokens=AGENT_TOKEN_LIMIT, debug=True)
            quiz_history = ""
            knowledge_backups_dir = workspace / "knowledge_backups"
            knowledge_backups_dir.mkdir(exist_ok=True)
            
            for round_num in range(1, 6):
                print(f"\n{'='*60}")
                print(f"ROUND {round_num} for {persona_name}")
                print(f"{'='*60}")
                
                if round_num == 1:
                    print("\n1. Initial knowledge discovery...")
                    summary = extract_knowledge_discovery(extractor, str(blocks_dir))
                    print(f"   Discovery summary length: {len(summary)} chars")
                else:
                    print("\n1. Searching for improvements based on feedback...")
                    summary = extract_knowledge_discovery(extractor, str(blocks_dir))
                    print(f"   Improvement summary length: {len(summary)} chars")
            
                print("\n2. Generating knowledge.md...")
                knowledge_content = generate_knowledge_md(extractor)
                content_length = len(knowledge_content)
                print(f"   Generated: {content_length} chars")
                
                knowledge_file = knowledge_dir / f"{persona_name}_knowledge_round{round_num}.md"
                knowledge_file.write_text(knowledge_content, encoding='utf-8')
                print(f"   Saved to {knowledge_file.name}")
                
                backup_file = knowledge_backups_dir / f"{persona_name}_backup_round{round_num}.md"
                backup_file.write_text(knowledge_content, encoding='utf-8')
            
                # Store the generated knowledge in extractor's memory for future rounds
                notify(extractor, f"""ROUND {round_num} KNOWLEDGE GENERATION COMPLETE

Based on your discovery and analysis of the blocks in {blocks_dir}, you have successfully generated a comprehensive knowledge document.

The knowledge.md you created ({content_length} characters) has been saved as:
- Primary: {knowledge_file.name}
- Backup: {backup_file.name}

This is the exact knowledge document you generated in this round:

---BEGIN KNOWLEDGE.MD ROUND {round_num}---
{knowledge_content}
---END KNOWLEDGE.MD ROUND {round_num}---

This knowledge will now be tested via quiz-based validation to identify gaps and areas for improvement in the next round.""")
                
                if not knowledge_content:
                    print("   Failed to generate knowledge.md")
                    continue
                
                print("\n3. Generating quiz...")
                quiz_agent = PolyAgent(id=f"quiz_generator_{persona_name}_round{round_num}", max_tokens=AGENT_TOKEN_LIMIT)
                quiz = generate_quiz(quiz_agent, all_pain_points, quiz_history if quiz_history else None)
                quiz_history = f"\n\nROUND {round_num}:\n{quiz}"
                print(f"   Quiz length: {len(quiz)} chars")
                
                print("\n4. Answering quiz with knowledge base...")
                answerer = PolyAgent(id=f"answerer_{persona_name}_round{round_num}", max_tokens=AGENT_TOKEN_LIMIT)
                answers = answer_quiz(answerer, knowledge_content, quiz)
                print(f"   Answers length: {len(answers)} chars")
                
                print("\n5. Scoring answers...")
                scorer = PolyAgent(id=f"scorer_{persona_name}_round{round_num}", max_tokens=AGENT_TOKEN_LIMIT)
                score_result = score_answers(scorer, all_pain_points, knowledge_content, quiz, answers)
                print(f"\n{score_result}")
                
                print("\n6. Extracting improvement suggestions...")
                suggestions = extract_improvement_suggestions(scorer)
                print(f"   Suggestions length: {len(suggestions)} chars")
                
                notify(extractor, f"""ROUND {round_num} FEEDBACK AND IMPROVEMENT GUIDANCE

Based on the quiz validation of your Round {round_num} knowledge document:
- A quiz was generated from the original pain points
- Your knowledge.md was used to answer the quiz
- The answers were scored to identify gaps

IMPROVEMENT SUGGESTIONS FOR ROUND {round_num + 1}:

{suggestions}

IMPORTANT: In the next round, you should:
1. Review your previous knowledge document (stored in your memory above)
2. Focus on the gaps and weaknesses identified in these suggestions
3. Search the blocks in {blocks_dir} for information addressing these gaps
4. Generate an improved, more comprehensive knowledge document""")
            
            print(f"\n\nKnowledge extraction complete for {persona_name} after 5 rounds.")
        
        print(f"\n\n{'='*60}")
        print("ALL PERSONAS COMPLETE")
        print(f"{'='*60}")
        print(f"All knowledge versions backed up in: {knowledge_backups_dir}")
        print(f"Final knowledge in: {knowledge_dir}")
        print("Check http://localhost:8765 for details")
        input("Press Enter to stop...")

if __name__ == "__main__":
    main()
