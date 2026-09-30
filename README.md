# URACE: Universal Recursive Autonomous Co-Founder Engine

> An enterprise-grade, AI-agnostic, state-driven, and AST-aware multi-agent orchestration pipeline designed for maximum quality per token. URACE replaces unstructured "vibecoding" with a self-healing, temporally synchronized, and atomically locked autonomous engineering loop featuring **universal platform and programming language agnosticism**.

---

## ⚡ Core Architecture & Capabilities

* **Platform & Language Agnosticism:** Automatically detects your host operating system (Linux, macOS, WSL/Git Bash) and analyzes project manifests (`package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, etc.) to configure execution paths, locking primitives, and AST parser grammars on the fly.
* **AST-Aware Semantic Caching:** Parses code via Abstract Syntax Trees and symbol graphs across any supported language, extracting only surgical function signatures and type declarations while stripping dead imports, comments, and whitespace to achieve absolute peak token efficiency.
* **Dynamic Model-Tier Routing (`scripts/router.sh`):** Automatically maps tasks to optimal model tiers based on complexity and provider readiness:
* *Deep Reasoning Tier:* Claude Code / Top-tier endpoints for architectural planning and cold boots.
* *Fast Execution Tier:* High-speed coding models for deterministic code generation.
* *Large-Window Tier:* Massive context models for codebase auditing and RAG sync.


* **Dual Bootstrap Phase (`scripts/init-env.sh`):**
* *Phase 1 (Cold-Bootstrap):* Auto-detects platform and stack, scaffolds `.agents/` and `scripts/`, and generates constitution files.
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

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.