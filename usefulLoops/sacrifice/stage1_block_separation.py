#!/usr/bin/env python3

from polycli import PolyAgent
from polycli.orchestration import session, pattern, serve_session
from polycli.builtin_patterns import notify
from pathlib import Path

@pattern
def split_file(agent: PolyAgent, filepath: str, output_dir: str, attempt: int):
    filename = Path(filepath).stem
    block_dir = Path(output_dir) / filename
    block_dir.mkdir(parents=True, exist_ok=True)
    
    prompt = f"""Split the file at {filepath} into 5-10 logical blocks using semantic analysis.

APPROACH:
1. Extract text snippets from different positions (e.g., at 1/10, 2/10, 3/10... of the file)
2. Read these snippets to understand what each section is about
3. Probe recursively to find natural SEMANTIC boundaries (not just syntactic markers)
4. Identify where topics/problems/solutions actually change
5. Use these semantic boundaries to split the file programmatically

Save each block as a separate markdown file in {block_dir}/

Requirements (HARD LIMITS - MUST PASS):
- Create between 5 and 10 block files (MANDATORY: will fail check otherwise)
- Name them block_1.md, block_2.md, etc.
- Total size of all blocks >= 50% of original file size (MANDATORY: will fail check otherwise)
- Each block should be semantically coherent (about the same topic/problem)
- Avoid content overlap between blocks
- Preserve exact content from the original file

This is attempt {attempt}.

After creating blocks, verify:
1. Number of files is between 5 and 10
2. Total size is >= 50% of original

Report back with the number of blocks created and total size."""
    
    result = agent.run(prompt, tracked=True)
    return result.content

def main():
    workspace = Path("workspace")
    raw_dir = workspace / "raw"
    blocks_dir = workspace / "blocks"
    blocks_dir.mkdir(exist_ok=True)
    
    files = list(raw_dir.glob("*.md"))
    if not files:
        print("No files found in workspace/raw/")
        return
    
    filepath = files[0]
    print(f"Processing {filepath.name}...")
    
    with session() as s:
        server, _ = serve_session(s, port=8765)
        print(f"Monitor at http://localhost:8765")
        
        agent = PolyAgent(id=f"splitter_{filepath.stem}")
        
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            result = split_file(agent, str(filepath), str(blocks_dir), attempt)
            print(f"  Attempt {attempt}: {result}")
            
            block_count = len(list((blocks_dir / filepath.stem).glob("*.md"))) if (blocks_dir / filepath.stem).exists() else 0
            
            if 5 <= block_count <= 10:
                original_size = filepath.stat().st_size
                total_block_size = sum(f.stat().st_size for f in (blocks_dir / filepath.stem).glob("*.md"))
                
                if total_block_size >= original_size * 0.5:
                    print(f"  Success: {block_count} blocks, {total_block_size}/{original_size} bytes")
                    break
                else:
                    failure_msg = f"Size check failed: {total_block_size} bytes < {original_size * 0.5} bytes (50% of original). Please create larger blocks."
                    print(f"  {failure_msg}")
                    notify(agent, failure_msg)
            else:
                failure_msg = f"Block count check failed: got {block_count} blocks, need between 5 and 10. Please adjust the number of blocks."
                print(f"  {failure_msg}")
                notify(agent, failure_msg)
            
            if attempt == max_attempts:
                print(f"  Failed after {max_attempts} attempts")
        
        print("\n\nBlock separation complete. Check http://localhost:8765 for details")
        input("Press Enter to stop...")

if __name__ == "__main__":
    main()
