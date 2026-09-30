# Universal Recursive Autonomous Co-Founder Engine

> **An enterprise-grade, AI-agnostic, state-driven, and AST-aware multi-agent orchestration pipeline designed for maximum quality per token. URACE replaces unstructured "vibecoding" with a self-healing, temporally synchronized, and atomically locked autonomous engineering loop featuring universal file-base, project-type, and programming language agnosticism.**

---

## ⚡ Core Architecture & Capabilities

* **Universal File-Base, Project-Type & Language Agnosticism:** Dynamically scans repositories using recursive glob discovery (inspecting arbitrary build manifests like `**/package.json`, `**/Cargo.toml`, `**/go.mod`, `**/pyproject.toml`, `**/Makefile`, `**/CMakeLists.txt`, etc.) and content heuristics rather than rigid root-filename assumptions. Automatically adapts shell locks, execution paths, and AST parser grammars on the fly, with support for manual environment overrides (`URACE_STACK`, `URACE_BUILD_CMD`, `URACE_TEST_CMD`) via `.agents/environment.env`.
* **AST-Aware Semantic Caching:** Parses code via Abstract Syntax Trees and symbol graphs across any supported language, extracting only surgical function signatures and type declarations while stripping dead imports, comments, and whitespace to achieve absolute peak token efficiency.
* **Dynamic Model-Tier Routing (`scripts/router.sh`):** Automatically maps tasks to optimal model tiers based on complexity and provider readiness:
* *Deep Reasoning Tier:* Claude Code / Top-tier endpoints for architectural planning and cold boots.
* *Fast Execution Tier:* High-speed coding models for deterministic code generation.
* *Large-Window Tier:* Massive context models for codebase auditing and RAG sync.


* **Dual Bootstrap Phase (`scripts/init-env.sh`):**
* *Phase 1 (Cold-Bootstrap):* Auto-detects platform and stack via universal heuristics, scaffolds `.agents/` and `scripts/`, and generates constitution files.
* *Phase 2 (First-Update):* Validates topological dependency graphs, checks AI readiness, and initializes vector caching.


* **Industrial-Grade Safety & Resilience (`scripts/auto-loop.sh`):**
* Cross-platform atomic file-locking on `.agents/active-spec.md` to prevent race conditions.
* Signal trapping (`Ctrl+C` abort protection) with non-destructive workspace stashing (`git stash push -m "URACE auto-stash on abort"`).
* Zero-breakage circuit breakers with automated test healing (`scripts/heal-tests.sh`) and consecutive-failure rollbacks (`git checkout .`).



---

## 🚀 Execution Modes

URACE adapts to your preferred level of oversight via clean command-line flags:

| Mode | Command | Description |
| --- | --- | --- |
| **Autonomous** | `./scripts/auto-loop.sh --autonomous` | Unsupervised end-to-end auto-chaining (Suggestions $\rightarrow$ Planning $\rightarrow$ Execution loop). |
| **Supervised** | `./scripts/auto-loop.sh --plan` | Interactive planning mode with structured architectural breakdowns. |
| **Man-in-the-Middle** | `./scripts/auto-loop.sh --check` | Pauses execution before code writing for diff inspection and manual spec approval. |
| **Proactive Suggestions** | `./scripts/auto-loop.sh --suggestions` | Scans codebase debt and generates an active suggestion backlog. |

---

## 🛠️ Quick Start & Initialization

1. **Configure API Keys:** In the project root, create a file named `.env` and add your required AI model API keys:
```env
ANTHROPIC_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
XAI_API_KEY=your_grok_api_key_here

```


2. **Execute Initial Bootstrap:** Run the updated agnostic bootstrap prompt (located in your execution context) inside your primary agent or execution environment to initialize the core scaffolding, universal heuristic discovery, and state parameters.
3. **Launch the Engine:**
```bash
chmod +x scripts/*.sh
./scripts/init-env.sh
./scripts/auto-loop.sh --autonomous

```



---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.