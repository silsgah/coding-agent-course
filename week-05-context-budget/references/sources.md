# Week 5 — References

## From the reference repos

### DecodingAI
- **Lesson 4 — Context Engineering:** memory injection, compaction, skills, LSP, footer gauge
- `src/decode/context/` — compaction + conversation log
- `src/decode/memory/` — AGENTS.md / MEMORY.md loading + write-back
- `src/decode/services/lsp/` — LSP client for context-aware code navigation

### NVIDIA NOOA
- **Context Blocks:** `examples/quickstart/08_context_blocks.py` — first-class context API
- **Summarization:** `examples/quickstart/09_summarization.py` — TokenBudgetSummarizer
- **Skills:** `examples/quickstart/10_skills.py` — TextSkill for domain knowledge
- **Paper results:** NOOA matches other harnesses at ~half the tokens

## NOOA Case Study Key Points

From the [NOOA paper](https://arxiv.org/abs/2607.20709):
- Agent-as-Python-object design naturally scopes context per method
- Type annotations serve as implicit prompt engineering (fewer tokens)
- Methods-as-tools eliminates separate tool schema definitions
- TokenBudgetSummarizer compresses between method calls, not within them
- Result: competitive performance with significantly lower token usage

## Articles
| Article | Why read it |
|---|---|
| [Context Engineering for AI Agents](https://www.decodingai.com/p/context-engineering) | The full context engineering framework |
| [Why MCP Breaks Old Enterprise AI Architectures](https://www.decodingai.com/p/why-mcp-breaks-old-enterprise-ai) | How MCP surfaces context from external services |
