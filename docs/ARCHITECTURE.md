# JARVIS OS Architecture

JARVIS OS is a personal AI operating layer. The system is intentionally model-independent, tool-driven, permission-aware, and designed to grow from a useful local assistant into a long-running multi-agent system without rewriting the core.

## Core flow

```text
USER
  ↓
VOICE / TEXT
  ↓
JARVIS INTERFACE
  ↓
ORCHESTRATOR
  ↓
CONTEXT + INTENT + PLAN + POLICY
  ↓
MODEL ROUTER / AGENT ROUTER / TOOL ROUTER
  ↓
TASK RUNTIME
  ↓
BACKGROUND WORKERS
  ↓
VERIFY
  ↓
MEMORY
  ↓
RESULT
```

## Architectural responsibilities

### core/
Owns orchestration and decisions. It should not know provider-specific API details.

### models/
Owns model registry, capability metadata, provider selection, fallback, privacy/cost rules, and future scoring.

### providers/
Owns vendor/runtime integrations such as Ollama, LM Studio, OpenAI, and future providers.

### agents/
Owns specialist reasoning workers such as coding, research, UI, file intelligence, productivity, and verification agents.

### tools/
Owns executable capabilities. Agents request tools; they do not directly manipulate the operating system.

### tasks/
Owns long-running task state, queues, workers, scheduling, retries, verification, and approval checkpoints.

### memory/
Owns working, episodic, semantic, project, task, and user memory.

### files/
Owns scanning, indexing, metadata extraction, semantic retrieval, and file watching.

### productivity/
Owns goals, roadmap tracking, daily planning, progress analysis, and follow-up logic.

### voice/
Owns speech input/output. Voice and text must converge into the same JARVIS core pipeline.

### interface/
Owns presentation only. Business logic and model decisions must stay outside the UI.

## Non-negotiable rules

1. UI never contains JARVIS intelligence.
2. Agents never directly access the OS; they use tools.
3. Tools execute actions but do not decide what JARVIS should do.
4. Agents never hard-code a specific AI model or vendor.
5. Model routing never executes tools.
6. The orchestrator coordinates; it does not implement every capability itself.
7. Destructive or externally visible actions pass through a permission layer.
8. Long-running work belongs in the task runtime.
9. An agent saying "done" is not verification. Results must be checked.
10. Memory stores useful structured information, not every conversation forever.
11. Private/local work should prefer local execution when practical.
12. Do not add infrastructure until a real requirement justifies it.

## Current implementation milestone

The first architecture milestone introduces:

- a structured `Task` object
- a deterministic first-pass `IntentEngine`
- a provider `ModelRegistry`
- a local-first `ModelRouter`
- standardized AI provider contracts
- cloud fallback while keeping provider logic outside `Brain`

This is the bridge from the current command-driven assistant to the future orchestrated system.

## Planned evolution

```text
V1  Personal assistant + tasks + goals + memory
V2  File intelligence
V3  Voice conversation
V4  Multi-model routing
V5  Specialist agents
V6  Background workers
V7  Computer/browser control
V8  Proactive productivity
V9  MCP integrations
V10 IoT / physical-world control
```
