#!/usr/bin/env python3

from polycli import PolyAgent
from polycli.orchestration import session, pattern, batch, serve_session
from pathlib import Path

@pattern
def extract_pain_points(agent: PolyAgent, block_file: str, output_dir: str, agent_num: int):
    output_path = Path(output_dir) / Path(block_file).stem / f"agent_{agent_num}_pain_points.md"
    
    prompt = f"""Read the conversation block at {block_file} and extract pain points.

Focus on finding:
- Problems encountered and their solutions
- Mistakes made and corrections applied  
- Things that didn't work as expected
- "Actually" moments where understanding changed
- Debugging discoveries
- Performance issues found
- Integration problems solved
- Workarounds developed

Create a markdown file at {output_path} with issue-solution pairs.

Format each pain point as:
## Issue: [Brief description]
[Detailed problem description]

**Solution:**
[How it was solved, including code snippets if relevant]

---

Be specific and technical. Include exact error messages, code snippets, and context."""
    
    result = agent.run(prompt, tracked=True)
    return result.content

@pattern
def merge_pain_points(merger: PolyAgent, block_name: str, pain_points_dir: str):
    block_dir = Path(pain_points_dir) / block_name
    merged_file = block_dir / "merged_pain_points.md"
    
    prompt = f"""Read the 3 pain point files in {block_dir}/:
- agent_1_pain_points.md
- agent_2_pain_points.md  
- agent_3_pain_points.md

Merge them into a single comprehensive file at {merged_file}

Instructions:
- Remove duplicates but keep all unique insights
- Consolidate similar issues into more comprehensive entries
- Preserve all technical details and code snippets
- Organize by importance/severity if possible
- Keep the same markdown format

The merged file should contain the best insights from all 3 agents."""
    
    result = merger.run(prompt, tracked=True)
    return result.content

def main():
    workspace = Path("workspace")
    blocks_base_dir = workspace / "blocks"
    pain_points_base_dir = workspace / "pain_points"
    
    # Find all persona directories
    persona_dirs = [d for d in blocks_base_dir.iterdir() if d.is_dir()]
    if not persona_dirs:
        print("No block directories found. Run stage1 first.")
        return
    
    with session() as s:
        server, _ = serve_session(s, port=8765)
        print(f"Monitor at http://localhost:8765")
        
        # Process each persona directory
        for persona_dir in persona_dirs:
            persona_name = persona_dir.name
            print(f"\nProcessing persona: {persona_name}")
            
            blocks_dir = blocks_base_dir / persona_name
            pain_points_dir = pain_points_base_dir / persona_name
            pain_points_dir.mkdir(parents=True, exist_ok=True)
            
            block_files = sorted(blocks_dir.glob("block_*.md"))
            
            for block_file in block_files:
                print(f"  Processing {block_file.name}...")
                
                block_pain_dir = pain_points_dir / block_file.stem
                block_pain_dir.mkdir(exist_ok=True)
                
                agent1 = PolyAgent(id=f"extractor_1_{block_file.stem}")
                agent2 = PolyAgent(id=f"extractor_2_{block_file.stem}")
                agent3 = PolyAgent(id=f"extractor_3_{block_file.stem}")
                
                with batch():
                    pp1 = extract_pain_points(agent1, str(block_file), str(pain_points_dir), 1)
                    pp2 = extract_pain_points(agent2, str(block_file), str(pain_points_dir), 2)
                    pp3 = extract_pain_points(agent3, str(block_file), str(pain_points_dir), 3)
                
                print(f"    3 agents extracted pain points in parallel")
                
                merger = PolyAgent(id=f"merger_{block_file.stem}")
                
                merged = merge_pain_points(merger, block_file.stem, str(pain_points_dir))
                print(f"    Merged pain points saved")
        
        print(f"\n\nPain point discovery complete.")
        print(f"Results saved in {pain_points_base_dir}")
        print("Check http://localhost:8765 for details")
        input("Press Enter to stop...")

if __name__ == "__main__":
    main()