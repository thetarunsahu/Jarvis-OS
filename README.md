<!-- =========================================================
                         JARVIS OS
     Personal AI Operating Layer — Built by Tarun Kumar Sahu
========================================================== -->

<div align="center">

<br/>

# ◈ J A R V I S&nbsp;&nbsp; O S

### `PERSONAL INTELLIGENCE // AGENTIC SYSTEM // DIGITAL OPERATING LAYER`

<br/>

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=18&duration=3000&pause=900&color=00E5FF&center=true&vCenter=true&width=850&lines=Not+another+chatbot.;An+intelligent+layer+between+you+and+your+digital+world.;Think.+Plan.+Delegate.+Execute.+Verify.+Remember.;Building+towards+a+real+personal+AI+system." alt="Typing SVG" />

<br/><br/>

[![Python](https://img.shields.io/badge/Python-0B1117?style=for-the-badge&logo=python&logoColor=00E5FF)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-0B1117?style=for-the-badge&logo=qt&logoColor=00E5FF)](https://doc.qt.io/qtforpython-6/)
[![Ollama](https://img.shields.io/badge/Ollama-0B1117?style=for-the-badge&logo=ollama&logoColor=00E5FF)](https://ollama.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-0B1117?style=for-the-badge&logo=openai&logoColor=00E5FF)](https://openai.com/)
[![Status](https://img.shields.io/badge/STATUS-EARLY_ALPHA-00E5FF?style=for-the-badge&labelColor=0B1117)](#-development-status)

<br/>

[![GitHub stars](https://img.shields.io/github/stars/thetarunsahu/Jarvis-OS?style=social)](https://github.com/thetarunsahu/Jarvis-OS/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/thetarunsahu/Jarvis-OS?style=social)](https://github.com/thetarunsahu/Jarvis-OS/network/members)

<br/>

> **JARVIS OS is an experimental personal AI operating layer designed to understand, remember, reason, use tools, coordinate AI agents and eventually interact with both the digital and physical world.**

</div>

---

## `> SYSTEM.VISION`

Most AI assistants wait for you to ask a question.

**JARVIS is being designed to do more.**

The long-term goal is to create a system capable of understanding a goal, gathering context, selecting the right intelligence, delegating work to specialized agents, executing tasks through tools, tracking progress and returning only when your attention is actually needed.

```text
You define the goal.

JARVIS handles the orchestration.
```

Instead of:

```text
Human → Prompt → AI → Text
```

JARVIS aims toward:

```text
Human
  │
  ▼
Intent
  │
  ▼
JARVIS
  │
  ├── Understand Context
  ├── Recall Memory
  ├── Plan Task
  ├── Select Model
  ├── Select Agent
  ├── Select Tools
  ├── Execute
  ├── Verify
  └── Remember
        │
        ▼
      Result
```

---

## `> WHY JARVIS?`

The goal is **not** to recreate a movie interface.

The goal is to explore what a real personal AI system could become.

Imagine saying:

> **"Jarvis, find the agriculture robot design I showed my mentor."**

JARVIS searches your files using context instead of requiring an exact filename.

Or:

> **"Jarvis, redesign this application's UI."**

JARVIS identifies the task, selects an appropriate model or specialist agent, gathers the required project files and begins the task.

Meanwhile, you continue working.

```text
YOU                              JARVIS

DSA                              ├── UI Agent
College Work                     ├── Research Agent
Learning                         ├── Coding Agent
Hackathons                       ├── File Agent
Projects                         └── Planner Agent
      │                                  │
      └──────── work in parallel ────────┘
```

That is the direction of **JARVIS OS**.

---

# `> SYSTEM ARCHITECTURE`

<div align="center">

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         J A R V I S   O S                           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                         ┌────────▼────────┐
                         │    INTERFACE    │
                         │  Voice / Text   │
                         │  Desktop HUD    │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  ORCHESTRATOR   │
                         │   JARVIS CORE   │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
        ┌─────▼─────┐       ┌─────▼─────┐       ┌────▼────┐
        │  MEMORY   │       │  PLANNER  │       │ CONTEXT │
        └─────┬─────┘       └─────┬─────┘       └────┬────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                         ┌────────▼────────┐
                         │   TASK ROUTER   │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼────────────────────┐
              │                   │                    │
      ┌───────▼───────┐   ┌───────▼───────┐    ┌──────▼──────┐
      │  MODEL ROUTER │   │  AGENT ROUTER │    │ TOOL ROUTER │
      └───────┬───────┘   └───────┬───────┘    └──────┬──────┘
              │                   │                    │
       ┌──────┴──────┐      ┌─────┴────────┐     ┌────┴─────────┐
       │             │      │              │     │              │
   LOCAL AI      CLOUD AI   FILE        CODING  FILES        TERMINAL
   Ollama        APIs       AGENT       AGENT   BROWSER      SYSTEM
   Qwen/etc.              RESEARCH       UI     GITHUB       APPS
                           PLANNER      AGENT    CALENDAR     IoT
       │             │         │          │       │             │
       └──────┬──────┘         └────┬─────┘       └──────┬──────┘
              │                     │                    │
              └─────────────────────┼────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │   TASK ENGINE   │
                           │ Queue / Workers │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │    EXECUTION    │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │     VERIFY      │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │     MEMORY      │
                           │  Learn Context  │
                           └────────┬────────┘
                                    │
                                    ▼
                                  DONE
```

</div>

---

# `> CORE PRINCIPLE`

JARVIS should never be permanently tied to one AI model.

```text
                           JARVIS
                              │
                         AI Provider
                              │
               ┌──────────────┼──────────────┐
               │              │              │
             Local          Cloud          Future
               │              │              │
            Ollama         OpenAI         Providers
               │
        Qwen / Gemma / ...
```

Models will change.

Providers will change.

The **system architecture should survive them.**

---

# `> CURRENT FOUNDATION`

JARVIS OS is currently in active early development.

| Capability | Status |
|---|:---:|
| Modular project architecture | ✅ |
| Command routing | ✅ |
| Local AI through Ollama | ✅ |
| AI provider abstraction | 🟢 |
| OpenAI provider foundation | 🟢 |
| Tool registry / execution | 🟢 |
| Persistent memory foundation | 🟢 |
| File operations | 🟢 |
| System information tools | ✅ |
| Desktop HUD / dashboard | 🟢 |
| Voice interaction | 🚧 |
| Semantic file search | 🧪 |
| Model router | 🧪 |
| Multi-agent orchestration | 🔬 |
| Background task workers | 🔬 |
| Personal productivity engine | 🔬 |
| Autonomous workflows | 🔭 |
| IoT / physical-world integration | 🔭 |

### Legend

```text
✅  Working foundation
🟢  Implemented / evolving
🚧  In development
🧪  Next-stage experiment
🔬  Planned architecture
🔭  Long-term vision
```

---

# `> PROJECT STRUCTURE`

```text
Jarvis-OS/
│
├── core/
│   ├── brain.py
│   ├── jarvis.py
│   └── router.py
│
├── providers/
│   ├── ai_provider.py
│   ├── ollama_provider.py
│   └── openai_provider.py
│
├── memory/
│   └── ...
│
├── tools/
│   └── ...
│
├── voice/
│   └── ...
│
├── interface/
│   ├── dashboard.py
│   └── widgets/
│
├── main.py
├── AGENTS.md
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Each module has a specific responsibility.

### `core/`

The central orchestration layer.

Responsible for understanding requests, routing commands and coordinating the rest of the system.

### `providers/`

AI model integrations.

The application should communicate with models through provider interfaces rather than becoming dependent on a single vendor.

### `tools/`

Capabilities JARVIS can execute.

Examples:

```text
filesystem
system
terminal
browser
applications
GitHub
calendar
future IoT devices
```

### `memory/`

Stores persistent and contextual knowledge required by JARVIS.

### `voice/`

Speech input, wake-word and speech-output systems.

### `interface/`

The visual desktop experience.

Includes the evolving futuristic HUD/dashboard built using **PySide6**.

---

# `> THE AGENT LAYER`

Future JARVIS will not be one massive AI prompt.

Tasks will be delegated to specialized workers.

```text
                         TASK
                          │
                     ┌────▼────┐
                     │ JARVIS  │
                     └────┬────┘
                          │
       ┌──────────────────┼───────────────────┐
       │                  │                   │
       ▼                  ▼                   ▼
   FILE AGENT         CODING AGENT        UI AGENT
       │                  │                   │
       ├ Find files       ├ Understand repo   ├ Analyse UI
       ├ Index data       ├ Modify code       ├ Design
       └ Retrieve         └ Test changes      └ Implement
       
       ▼                  ▼                   ▼
 RESEARCH AGENT       PLANNER AGENT      COLLEGE AGENT
       │                  │                   │
       ├ Search           ├ Goals             ├ Deadlines
       ├ Compare          ├ Schedule          ├ Assignments
       └ Summarize        └ Follow-up         └ Progress
```

The user should interact primarily with **JARVIS**.

JARVIS handles the rest.

---

# `> MODEL ROUTER`

Different tasks need different intelligence.

The long-term model router will select models based on:

```text
Task complexity
      +
Reasoning requirement
      +
Coding capability
      +
Vision capability
      +
Latency
      +
Cost
      +
Privacy
      +
Local hardware
```

Example:

```text
Quick local request
        │
        ▼
   Small Local LLM

Private file analysis
        │
        ▼
     Local Model

Complex reasoning
        │
        ▼
 Strong Cloud Model

UI / Visual task
        │
        ▼
Multimodal AI Model

Image generation
        │
        ▼
  Image Generator
```

The user should not have to constantly choose models manually.

---

# `> MEMORY SYSTEM`

A useful personal AI needs more than chat history.

JARVIS is being designed around multiple layers of memory.

```text
                JARVIS MEMORY
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
   SHORT TERM     LONG TERM      WORKING MEMORY

 Current task     Preferences      Active context
 Conversation     Projects         Current files
 Temporary data   Goals            Task state
                  History
```

Eventually JARVIS should understand references such as:

> "Open that robot design I worked on last month."

without requiring the user to remember:

```text
D:\Projects\Agribot\design\final_final_v7_real.png
```

---

# `> BACKGROUND EXECUTION`

A central goal of JARVIS OS is **parallel productivity**.

```text
USER
│
├── DSA
├── College Work
├── Learning
└── Hackathon
        │
        │
        │           JARVIS
        │              │
        │       ┌──────┼──────┐
        │       ▼      ▼      ▼
        │     Worker Worker Worker
        │       │      │      │
        │      UI   Research Code
        │       │      │      │
        │       └──────┼──────┘
        │              │
        │              ▼
        │          TASK READY
        │              │
        └──────────────◄┘
```

JARVIS should work **for the user**, not become another application that demands constant attention.

---

# `> SECURITY MODEL`

Autonomous systems require boundaries.

Not every action should have equal permission.

```text
LEVEL 0 ─ READ
         Search files
         Read information
         Analyse context

LEVEL 1 ─ SAFE ACTION
         Open files
         Open applications
         Create drafts

LEVEL 2 ─ MODIFY
         Edit files
         Change project content

LEVEL 3 ─ SENSITIVE
         Delete files
         Send messages
         Push production code
         Install software

LEVEL 4 ─ CRITICAL
         Financial actions
         Credential changes
         Destructive operations
```

Sensitive actions should require explicit confirmation.

> **Intelligence without permission boundaries is not automation — it is risk.**

---

# `> TECHNOLOGY STACK`

<div align="center">

| Layer | Technology |
|---|---|
| Core | Python |
| Desktop UI | PySide6 / Qt |
| Local AI | Ollama |
| Cloud AI | Provider-based APIs |
| Communication | HTTP / JSON |
| System Monitoring | psutil |
| Configuration | python-dotenv |
| Architecture | Modular Provider + Tool System |
| Future Storage | Persistent + Semantic Memory |
| Future Execution | Async Workers / Task Queue |
| Future Intelligence | Multi-Agent Orchestration |

</div>

---

# `> INSTALLATION`

### 1. Clone the repository

```bash
git clone https://github.com/thetarunsahu/Jarvis-OS.git
cd Jarvis-OS
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

and configure the providers you want to use.

### 5. Start JARVIS

```bash
python main.py
```

---

# `> DEVELOPMENT PHILOSOPHY`

JARVIS OS follows a few important rules.

```text
01 // BUILD REAL CAPABILITIES
     No fake demo features.

02 // KEEP MODULES SEPARATE
     Memory should not become UI.
     UI should not become the brain.
     Providers should not become the core.

03 // PROVIDER INDEPENDENCE
     Never design the entire system around one AI company.

04 // MINIMUM NECESSARY COMPLEXITY
     Do not introduce infrastructure without a real reason.

05 // VERIFY BEFORE AUTONOMY
     Execution must be observable and testable.

06 // HUMAN REMAINS IN CONTROL
     Sensitive actions require explicit permission.
```

---

# `> ROADMAP`

### PHASE 01 — FOUNDATION

```text
[x] Core architecture
[x] Command router
[x] Tool system
[x] Memory foundation
[x] Local AI provider
[x] Cloud provider foundation
[x] Desktop HUD foundation
```

### PHASE 02 — PERSONAL ASSISTANT

```text
[ ] Natural voice conversation
[ ] Goals and task tracking
[ ] Daily planning
[ ] Reminders
[ ] Progress tracking
[ ] Long-term user memory
[ ] Semantic file retrieval
```

### PHASE 03 — INTELLIGENCE ROUTING

```text
[ ] Model router
[ ] Local / cloud decision engine
[ ] Context manager
[ ] Cost-aware routing
[ ] Capability-aware model selection
```

### PHASE 04 — AGENTIC SYSTEM

```text
[ ] File Agent
[ ] Research Agent
[ ] Coding Agent
[ ] UI Agent
[ ] Planner Agent
[ ] College Agent
[ ] Agent orchestration
```

### PHASE 05 — AUTONOMOUS EXECUTION

```text
[ ] Background task engine
[ ] Worker queues
[ ] Task status dashboard
[ ] Result verification
[ ] Retry / recovery system
[ ] Human approval checkpoints
```

### PHASE 06 — JARVIS OS

```text
[ ] Deep desktop integration
[ ] Application control
[ ] Browser automation
[ ] Development workflows
[ ] Proactive intelligence
[ ] Context-aware assistance
[ ] Multi-device synchronization
```

### PHASE 07 — PHYSICAL WORLD

```text
[ ] IoT integration
[ ] ESP32 communication
[ ] Sensors
[ ] Robotics
[ ] Smart environment control
```

---

# `> ENDGAME`

The final vision is simple to describe.

Hard to build.

```text
                          YOU
                           │
                           ▼
                    ┌────────────┐
                    │   JARVIS   │
                    └─────┬──────┘
                          │
     ┌────────────────────┼─────────────────────┐
     │                    │                     │
     ▼                    ▼                     ▼
 UNDERSTAND             THINK                 REMEMBER
     │                    │                     │
     └────────────────────┼─────────────────────┘
                          ▼
                         PLAN
                          │
                          ▼
                      DELEGATE
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
            AI          AGENTS        TOOLS
             │            │            │
             └────────────┼────────────┘
                          ▼
                       EXECUTE
                          │
                          ▼
                        VERIFY
                          │
                          ▼
                         LEARN
```

### One interface.

### Multiple intelligences.

### Persistent context.

### Real execution.

### Human control.

<br/>

<div align="center">

## `JARVIS IS NOT THE MODEL.`

### `JARVIS IS THE SYSTEM THAT DECIDES HOW INTELLIGENCE GETS USED.`

<br/>

---

### Built from scratch. One subsystem at a time.

<br/>

**Created by [Tarun Kumar Sahu](https://github.com/thetarunsahu)**

<br/>

`JARVIS OS // PERSONAL INTELLIGENCE PROJECT`

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00151C,50:003847,100:00E5FF&height=120&section=footer" width="100%"/>

</div>
