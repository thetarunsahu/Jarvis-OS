# JARVIS-OS — Agent Development Rules

## Mission

Build JARVIS-OS as a real, modular personal AI system.

JARVIS should eventually be able to:

- understand natural language
- use tools
- remember useful context
- plan multi-step tasks
- interact with the computer
- communicate through voice
- optionally interact with IoT hardware
- provide a clear visual interface

The goal is not to build a fake demo.
Every major capability should work end-to-end.

---

# 1. MINIMUM NECESSARY IMPLEMENTATION

Before writing new code:

1. Check whether the capability already exists.
2. Reuse existing project code whenever possible.
3. Prefer Python standard library when sufficient.
4. Prefer existing dependencies already installed.
5. Prefer OS-native functionality when practical.
6. Use a new dependency only when it provides clear value.
7. Do not create abstractions without a real current need.

Do not over-engineer.

---

# 2. ARCHITECTURE

Keep responsibilities separated.

### core/

Contains JARVIS orchestration and decision-making.

### providers/

Contains AI model integrations.

Examples:

- Ollama / Qwen
- NVIDIA
- OpenAI
- future providers

The core should not depend directly on a specific AI provider.

### tools/

Contains actions JARVIS can execute.

Examples:

- filesystem
- system information
- applications
- terminal
- browser
- IoT

### memory/

Contains persistent and contextual memory.

### voice/

Contains speech input and speech output.

### interface/

Contains the user interface and dashboard.

---

# 3. PROVIDER ABSTRACTION

Never hard-code a specific model into the entire application.

Use the provider interface.

Example:

```text
JARVIS
   ↓
Brain
   ↓
AIProvider
   ├── OllamaProvider
   ├── NVIDIAProvider
   └── OpenAIProvider