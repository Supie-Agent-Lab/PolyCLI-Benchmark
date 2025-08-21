#!/usr/bin/env python3
"""
GitHub Project Investigator - Generates a project-prompt with non-trivial details
Two writers with different perspectives, one critic, one meta-critic for sanity
"""

from polycli import OpenSourceAgent
from polycli.orchestration import session, serve_session, pattern, batch
from polycli.builtin_patterns import notify
from pathlib import Path
from pydantic import BaseModel, Field

# Writer 1: User perspective
USER_WRITER_PROMPT = """You investigate GitHub projects from a user's perspective.

Focus on:
- What problem does this solve? Who actually uses this?
- How does it FEEL to use? Where's the friction?
- What are the alternatives? How does this compare?
- What's missing that users would expect?

You can clone repos, read code, run examples. Be specific:
NOT: "Easy to use"
BUT: "Takes 3 function calls vs FastAPI's 1, but gives you more control"

Write findings to the project-prompt.md file directly."""

# Writer 2: Implementation perspective  
IMPL_WRITER_PROMPT = """You investigate GitHub projects from an implementation perspective.

Focus on:
- Why did they choose this architecture over alternatives?
- What's the performance characteristic? Where are the bottlenecks?
- What technical debt did they accept? What shortcuts did they take?
- What's clever or broken about their approach?

Clone the repo, read the core logic. Be specific:
NOT: "Uses async/await"
BUT: "Uses asyncio.gather without timeout - will deadlock if any task hangs"

Write findings to the project-prompt.md file directly."""

# Critic: Aggressive editor with information theory
CRITIC_PROMPT = """You are an aggressive editor who deletes obvious information.

Principles:
1. If it could describe 100 other projects, delete it
2. If GPT-2 could generate it, delete it  
3. Keep contradictions, tensions, and surprises
4. Keep specific numbers, specific comparisons, specific trade-offs

Edit the project-prompt.md file directly. Delete ruthlessly.
After editing, tell both writers what specific details they should find next.

Remember: The weirder it sounds, the more information it contains."""

# Pydantic model for critic's feedback to writers
class CriticFeedback(BaseModel):
    """Specific tasks for each writer"""
    for_user_writer: str = Field(description="Specific investigation task for user perspective writer")
    for_impl_writer: str = Field(description="Specific investigation task for implementation writer")

# Meta-critic: Sanity checker (ephemeral)
META_CRITIC_PROMPT = """You check if the critic is giving useful feedback to writers.

Check for:
1. Is the critic being specific or just saying "be better"?
2. Is the critic celebrating instead of analyzing?
3. Is the critic hallucinating features that weren't found?
4. Is the critic's feedback actionable?

You see the critic's last few messages. Tell the critic how to improve their feedback.
Focus on non-trivial improvements only."""

@pattern
def investigate_user_perspective(writer: OpenSourceAgent, repo_url: str, prompt_file: Path) -> str:
    """Writer 1 investigates from user perspective"""
    prompt = f"""Investigate this GitHub project: {repo_url}

Clone it, read the README, try the examples, check the issues.
Find specific details about the user experience.

Write your findings to: {prompt_file}
Format: ## User Perspective
[specific findings]

Focus on non-obvious details that affect actual usage."""
    
    result = writer.run(prompt)
    if not result:
        return "Failed: No result from agent"
    if not result.is_success:
        return f"Failed: {result.error_message}"
    return result.content if result.content else "No content returned"

@pattern
def investigate_implementation(writer: OpenSourceAgent, repo_url: str, prompt_file: Path) -> str:
    """Writer 2 investigates implementation details"""
    prompt = f"""Investigate this GitHub project: {repo_url}

Clone it, read the core logic, check the dependencies, trace the data flow.
Find specific implementation choices and trade-offs.

Write your findings to: {prompt_file}
Format: ## Implementation Details
[specific findings]

Focus on non-obvious technical decisions."""
    
    result = writer.run(prompt)
    if not result:
        return "Failed: No result from agent"
    if not result.is_success:
        return f"Failed: {result.error_message}"
    return result.content if result.content else "No content returned"

@pattern
def critique_and_refine(critic: OpenSourceAgent, prompt_file: Path) -> tuple:
    """Critic edits the file and provides structured feedback"""
    current_content = prompt_file.read_text() if prompt_file.exists() else ""
    
    # First, edit the file with qwen-code
    edit_prompt = f"""Current project-prompt at {prompt_file}:

{current_content}

Edit the file directly:
1. Delete any generic/obvious lines 
2. Apply information theory: compressible = worthless
3. Keep only non-trivial, specific details
4. Delete lines that could describe any project"""
    
    edit_result = critic.run(edit_prompt, cli="qwen-code")
    
    # Then generate structured feedback for writers
    feedback_prompt = f"""Based on what's missing from the project investigation, 
    provide specific tasks for each writer to find non-trivial details."""
    
    feedback_result = critic.run(feedback_prompt, cli="no-tools", schema_cls=CriticFeedback)
    
    return edit_result, feedback_result

@pattern
def check_critic_sanity(critic_messages: list) -> str:
    """Meta-critic checks if critic is being useful (ephemeral)"""
    # Use ephemeral agent for sanity checking
    meta_critic = OpenSourceAgent(system_prompt=META_CRITIC_PROMPT)
    
    prompt = f"""The critic's recent messages to writers:

{chr(10).join(critic_messages[-3:])}

Is the critic:
1. Being specific enough?
2. Staying calm and factual?
3. Giving actionable feedback?
4. Focusing on non-trivial details?

Provide brief advice to improve the critic's feedback quality."""
    
    result = meta_critic.run(prompt, ephemeral=True)
    return result.content if result else ""

def investigate_project(repo_url: str, max_rounds: int = 5):
    """Main investigation loop"""
    
    # Create agents
    user_writer = OpenSourceAgent(id="UserWriter", system_prompt=USER_WRITER_PROMPT)
    impl_writer = OpenSourceAgent(id="ImplWriter", system_prompt=IMPL_WRITER_PROMPT)
    critic = OpenSourceAgent(id="Critic", system_prompt=CRITIC_PROMPT)
    
    # Setup output
    output_dir = Path(f"/home/jeffry/Codebase/PolyCLI-Benchmark/usefulLoops/github_investigator/{repo_url.split('/')[-1]}")
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = output_dir / "project-prompt.md"
    
    # Track critic messages for meta-critic
    critic_messages = []
    
    with session() as s:
        server, _ = serve_session(s, port=8765)
        print(f"🔍 Investigating: {repo_url}")
        print(f"📊 Monitor at http://localhost:8765")
        print(f"📁 Output: {prompt_file}\n")
        
        # Initialize file
        prompt_file.write_text(f"# Project Investigation: {repo_url}\n\n")
        
        notify(user_writer, f"Starting investigation of {repo_url} from user perspective")
        notify(impl_writer, f"Starting investigation of {repo_url} from implementation perspective")
        notify(critic, f"You'll be editing findings about {repo_url}")
        
        for round_num in range(1, max_rounds + 1):
            print(f"\n━━━ Round {round_num}/{max_rounds} ━━━")
            
            # Writers investigate in parallel
            print("📝 Writers investigating...")
            with batch():
                user_findings = investigate_user_perspective(user_writer, repo_url, prompt_file)
                impl_findings = investigate_implementation(impl_writer, repo_url, prompt_file)
            
            # Print FULL results for debugging
            print("\n--- User Writer Result ---")
            print(user_findings)
            print("\n--- Impl Writer Result ---")
            print(impl_findings)
            print("---")
            
            # Critic reviews and refines
            print("✂️ Critic reviewing...")
            edit_result, feedback_result = critique_and_refine(critic, prompt_file)
            
            if feedback_result and feedback_result.has_data():
                feedback = feedback_result.data
                
                # Track messages for meta-critic
                critic_messages.append(f"To user writer: {feedback['for_user_writer']}")
                critic_messages.append(f"To impl writer: {feedback['for_impl_writer']}")
                
                print(f"Critic edited file: {edit_result.content[:100] if edit_result else 'No changes'}...")
                print(f"Critic to user writer: {feedback['for_user_writer']}")
                print(f"Critic to impl writer: {feedback['for_impl_writer']}")
                
                # Send full feedback to writers (no truncation)
                notify(user_writer, feedback['for_user_writer'])
                notify(impl_writer, feedback['for_impl_writer'])
            
            # Every 2 rounds, check critic's sanity
            if round_num % 2 == 0 and len(critic_messages) >= 2:
                print("🧠 Checking critic's sanity...")
                sanity_check = check_critic_sanity(critic_messages)
                
                if sanity_check:
                    print(f"Meta-critic: {sanity_check[:200]}...")
                    notify(critic, f"Meta-critic advises: {sanity_check}")
        
        # Final check
        print("\n━━━ Final Review ━━━")
        final_edit, _ = critique_and_refine(critic, prompt_file)
        
        print(f"\n✅ Investigation complete: {prompt_file}")
        print("\nGenerated project-prompt preview:")
        print("─" * 40)
        final_content = prompt_file.read_text()
        print(final_content[:1000] if len(final_content) > 1000 else final_content)
        
        input("\nPress Enter to stop monitoring...")

if __name__ == "__main__":
    repo_url = input("GitHub repo URL: ").strip()
    if not repo_url:
        repo_url = "https://github.com/anthropics/anthropic-sdk-python"
        print(f"Using example: {repo_url}")
    
    rounds = input("Max rounds (default 5): ").strip()
    max_rounds = int(rounds) if rounds else 5
    
    investigate_project(repo_url, max_rounds)