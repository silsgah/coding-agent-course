# Week 1 — References

## From the reference repos

### DecodingAI: Building a Coding Agent From Scratch
- **Lesson 1 — System Design:** The harness-vs-loop-vs-model framing.
  The run script (`lessons/01-system-design/run.sh`) runs a headless agent that maps its own source tree.
- **Lesson 2 — Agent Loop:** The ReAct turn, the y/n gate, steering mid-turn, and the provider seam.
  Source: `src/decode/agent/`, `src/decode/tools/`, `src/decode/harness/`

### Key source files to study
- `src/decode/agent/` — The Pydantic AI ReAct loop
- `src/decode/tools/` — file I/O, bash, web, todo, skills dispatch
- `src/decode/permissions/` — allow/ask/deny permission system
- `src/decode/harness/` — message queue + priority gate around the loop

## Articles

| Article | Why read it |
|---|---|
| [The Anatomy of an Agent Harness (LangChain)](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) | The experiment proving the harness is the real lever |
| [Agentic Harness Engineering](https://www.decodingai.com/p/agentic-harness-engineering) | The lesson thesis: the harness decides agent quality |
| [Tool Calling From Scratch to Production](https://www.decodingai.com/p/tool-calling-from-scratch-to-production) | The 5-step request-execute-respond tool loop |
| [Building Production ReAct Agents](https://www.decodingai.com/p/building-production-react-agents) | A production ReAct loop dissected from source |
| [LLM Agents Demystified](https://www.decodingai.com/p/llm-agents-demystified) | ReAct thought→action→observation loop explained |
| [AI Agents in 5 Levels of Difficulty](https://www.decodingai.com/p/ai-agents-in-5-levels-of-difficulty) | Progression from basic tool-calling to full agentic systems |
