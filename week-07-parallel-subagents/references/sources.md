# Week 7 — References

## From the reference repos

### DecodingAI
- **Lesson 6 — Subagents:** agents catalog, parallel Explore fan-out, compressed reports
- `src/decode/agents/` — Build / Plan / Code-Reviewer + Explore subagent

### NVIDIA NOOA
- **Self-extending agents:** LLM defines helper methods at runtime, fans them out with `asyncio.gather`
- **LLM cascading:** Different models for different method calls — cheap model for exploration, expensive model for synthesis

## Articles
| Article | Why read it |
|---|---|
| [AI Agents in 5 Levels of Difficulty](https://www.decodingai.com/p/ai-agents-in-5-levels-of-difficulty) | Level 5: multi-agent coordination |
| [Build, Configure, or Use As-Is](https://www.decodingai.com/p/agentic-harness-system-design) | When to build custom agent coordination vs use a framework |
