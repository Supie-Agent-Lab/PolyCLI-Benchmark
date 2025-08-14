#!/usr/bin/env python3
"""
Information Edge - Finding the rare gems that matter (with session tracking)
"""

from polycli import OpenSourceAgent
from polycli.orchestration import session, serve_session, pattern
from polycli.builtin_patterns import notify
from pathlib import Path

HUNTER_PROMPT = """You are an information edge hunter. Your goal is NOT to summarize or collect everything.
Your goal is to find the 1% of information that gives 99% of the advantage.

Principles:
1. Common knowledge is worthless. If it's on Wikipedia's first paragraph, skip it.
2. Look for: anomalies, contradictions, underground knowledge, expert blind spots, future indicators
3. One rare insight > 100 common facts
4. Follow the weird threads - they often lead to gold
5. What insiders know but don't say publicly
6. What experts assume but never verify
7. Where conventional wisdom is 180° wrong

You have web search. You can write scraping code. Use them creatively."""

REFINER_PROMPT = """You are a brutal information critic. 

Look at what we've collected and be harsh:
- Is this ACTUALLY rare or just seems rare?
- Will this matter in 6 months?
- Does this change any decisions?
- Is this signal or noise?

Delete the noise. Keep only diamonds.
Then think: what question would lead us to even rarer information?"""

@pattern
def hunt_for_edge(hunter: OpenSourceAgent, topic: str, edge_file_path: Path, round_num: int) -> str:
    """Hunt for one piece of rare information"""
    current_edge = edge_file_path.read_text() if edge_file_path.exists() else "Empty"
    
    prompt = f"""Topic: {topic}

Current edge file at {edge_file_path}:
{current_edge}

Find ONE piece of genuinely rare, valuable information about this topic.
Not summary. Not overview. One specific edge.

Search the weird corners. The contrarian views. The insider knowledge.
What would make someone say "I didn't know that, and it changes things"?

After finding it, append it to the file at: {edge_file_path}
Format: ## Round {round_num}
[your rare finding]"""
    
    result = hunter.run(prompt)
    return result.content if result else ""

@pattern
def refine_and_redirect(refiner: OpenSourceAgent, edge_file_path: Path) -> str:
    """Refine the collected information and suggest new directions"""
    current_content = edge_file_path.read_text() if edge_file_path.exists() else "Empty"
    
    prompt = f"""Look at our current edge information in file: {edge_file_path}

{current_content}

1. Delete any line that isn't genuinely rare/valuable by editing the file directly at: {edge_file_path}
2. What's the most promising thread we haven't pulled yet?
3. What question would lead to even rarer information?

Be brutal. Keep only diamonds. Edit the file to remove noise."""
    
    result = refiner.run(prompt)
    return result.content if result else ""

def edge_loop_with_session(topic: str, max_rounds: int = 10):
    """Information edge loop with session tracking"""
    
    # Create agents
    hunter = OpenSourceAgent(id="Hunter", system_prompt=HUNTER_PROMPT)
    refiner = OpenSourceAgent(id="Refiner", system_prompt=REFINER_PROMPT)
    
    # Setup output
    output_dir = Path(f"/home/jeffry/Codebase/PolyCLI-Benchmark/usefulLoops/edge_{topic.replace(' ', '_')}")
    output_dir.mkdir(exist_ok=True)
    edge_file = output_dir / "edge.md"
    
    with session() as s:
        # Start web UI
        server, _ = serve_session(s, port=8765)
        print(f"\n🌐 Monitor at http://localhost:8765")
        print(f"🎯 Hunting for edge on: {topic}\n")
        
        # Initialize edge file
        edge_file.write_text(f"# Information Edge: {topic}\n\n")
        notify(hunter, f"Starting hunt for information edge on: {topic}")
        notify(refiner, f"You'll be refining information about: {topic}")
        
        for round_num in range(1, max_rounds + 1):
            print(f"\n───── Round {round_num} ─────")
            
            # Hunt for rare information (hunter will write to file directly)
            edge_found = hunt_for_edge(hunter, topic, edge_file, round_num)
            
            if edge_found:
                print(f"Hunter action: {edge_found[:200]}...")
                notify(refiner, f"New edge found in round {round_num}")
            
            # Every 3 rounds, refine and redirect
            if round_num % 3 == 0:
                print("\n🔍 Refining...")
                suggestions = refine_and_redirect(refiner, edge_file)
                
                if suggestions:
                    print(f"Refiner: {suggestions[:200]}...")
                    notify(hunter, f"Refiner suggests: {suggestions[:500]}")
        
        print(f"\n✅ Edge information saved to: {edge_file}")
        print("\nFinal edge preview:")
        print("─" * 40)
        final_content = edge_file.read_text()
        print(final_content[-1000:] if len(final_content) > 1000 else final_content)
        
        input("\nPress Enter to stop monitoring...")

if __name__ == "__main__":
    topic = input("Topic: ").strip() or "AI agent architectures"
    rounds = input("Max rounds (default 10): ").strip()
    max_rounds = int(rounds) if rounds else 10
    
    edge_loop_with_session(topic, max_rounds)