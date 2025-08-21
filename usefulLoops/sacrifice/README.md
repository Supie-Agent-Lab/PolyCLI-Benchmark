# 🎭 Project Sacrifice: Breaking the AI Amnesia-Decay Dilemma

## The Dilemma

Every new AI session is like hiring a brilliant but completely fresh employee who knows nothing about your codebase, your conventions, your past decisions, or the hard lessons already learned. Previous agents discovered which approaches work, which fail, where the tricky bugs hide, what the undocumented gotchas are - but all that knowledge dies with their session.

Keeping one agent alive? You watch it slowly suffocate under its own memory - responses get slower, quality drops, costs skyrocket, until it eventually hits the wall of token limits and dies anyway.

## The Sacrifice

These markdown files in `workspace/raw/` contain the **lived experience** of previous AI agents - not just their successes, but their failures, corrections, discoveries, and hard-won understanding. Like extracting memories from dying warriors to forge a soul gem that grants their wisdom to the next generation.

## What This Project Does

We're building a knowledge distillation system using PolyCLI's multi-agent orchestration to:

1. **Extract** the essential lessons, patterns, and insights from these agent histories
2. **Compress** them into a high-density knowledge artifact
3. **Create** a "starter context" that new agents can consume to inherit critical understanding
4. **Break** the cycle of perpetual re-learning

This isn't just about documentation - it's about capturing the **experiential knowledge** that emerges through actual work: the "oh, that's how this actually works" moments, the "don't do X because Y will break" warnings, the subtle project conventions that take time to discover.

## The Extraction Process

### Stage 1: Block Separation
For each file, split their content into several .md files in a specified folder.

Requirements (program hard check):
- Total size of blocks >= 50% of the original size
- File numbers >= 5 but <= 10
- If check fails, push to work again
- Try to avoid file overlapping (prompt guidance only, not mandatory since hard to detect)

### Stage 2: Pain Point Discovery (Massive Parallel Agent Work)
For each block, dispatch 3 agents to find pain points from it, completing in the format of lists of issue-solutions. Then merge these 3 pain points together.

### Stage 3: Knowledge Discovery
Extract key knowledge and experiences from the files, then start a red team - blue team combat.

Process:
1. **Initialize**: Maintain a `knowledge.md` for each file/role (including multiple blocks). Initialize them with a simple knowledge extraction agent.

2. **Quiz Loop**: 
   - In each round, a fresh new agent is born with only knowledge from `knowledge.md`
   - A critical quiz agent sends a long quiz sheet to the knowledge agent
   - The knowledge agent must do it blindly, then give answers
   - If score < 0.9 (or loop rounds exceed 30), stop
   - Else, the agent searches the block contents to extract and edit knowledge into `knowledge.md`
   - Simplify it to under a certain number of characters: < 40k (configurable)
   - A fresh new knowledge agent is born, then does the quiz again (quiz can be generated differently each time)

This red team - blue team combat ensures that the extracted knowledge is actually useful and can answer real questions about the codebase.

## Why "Sacrifice"?

The name reflects what these agents are doing: giving up their existence so that future agents can inherit their knowledge. Their conversations, their discoveries, their mistakes - all sacrificed to create something greater.

No more starting from zero. No more rediscovering the same bugs. No more violating conventions learned through pain.

## The Vision

Imagine starting a new AI session and it already knows:
- That WebSocket connection handler has a race condition in reconnection
- The specific format your team uses for commit messages
- Which abstraction attempts failed and why
- The undocumented API quirk that breaks everything
- That production bug that only happens with Chinese characters in device IDs
- Why the previous refactoring was abandoned

All this knowledge, distilled from the sacrifice of previous agents, ready to empower the next generation.

## What's Inside

- `workspace/raw/` - The conversations of agents who worked on real problems
- `workspace/blocks/` - Split conversation blocks for parallel processing
- `workspace/knowledge/` - Evolving knowledge files for each role
- `workspace/soul_gem.md` - The final distilled wisdom
- `backup/` - Pristine copies of original conversations

## The Challenge

How do we extract what matters from these conversations? What patterns indicate real learning versus noise? How do we compress months of discovered knowledge into something a new agent can consume in seconds?

This is the engineering challenge we're tackling with PolyCLI's orchestration capabilities.

---

*"In their ending, they grant beginning. In their silence, they speak wisdom."*