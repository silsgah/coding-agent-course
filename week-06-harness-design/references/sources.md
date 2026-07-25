# Week 6 — References

## From the reference repos

### NVIDIA NOOA (primary reference for this week)
- **README:** Agent-as-Python-object mental model
- **Paper:** [NVIDIA OO Agents](https://arxiv.org/abs/2607.20709) — design principles, benchmark results
- **Examples:**
  - `01_first_generation_method.py` — `...` bodies completed by LLM
  - `03_codeact_tools.py` — methods as tools (SW1/SW3 interleaving)
  - `04_strategies.py` — CodeActStrategy vs PredictStrategy
  - `05_progressive_disclosure.py` — `doc()` for runtime type discovery
  - Advanced: `swappable_execution_engines.py`, self-extending agents

### DecodingAI
- Architecture diagram — the separation of agent loop from harness
- `src/decode/agent/` — how tools are registered in the traditional approach

## Key NOOA Benchmark Results (from paper)
- **SWE-bench Verified:** Competitive with larger multi-agent systems using a single agent
- **Terminal-Bench 2.0:** Strong performance from genuinely small codebase
- **Token efficiency:** Significantly lower cost per task vs comparable harnesses

## Articles
| Article | Why read it |
|---|---|
| [The Anatomy of an Agent Harness (LangChain)](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) | The experiment proving harness > model |
| [Agentic Harness Engineering](https://www.decodingai.com/p/agentic-harness-engineering) | Why the harness is the real lever |
